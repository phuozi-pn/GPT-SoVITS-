from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from voice_platform.auth.models import UserRow
from voice_platform.config import get_settings
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.models import UsageRecordRow
from voice_platform.quota.period import current_billing_month, next_reset_at
from voice_platform.quota.schemas import QuotaSummary, UserUsageReportRow
from voice_platform.wallet.repository import InsufficientWalletBalanceError, UserWalletRepository


class QuotaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._settings = get_settings()

    def _chars_used(self, user_id: UUID, billing_month: str) -> int:
        used = self._session.scalar(
            select(func.coalesce(func.sum(UsageRecordRow.amount), 0)).where(
                UsageRecordRow.user_id == user_id,
                UsageRecordRow.billing_month == billing_month,
                UsageRecordRow.record_type == "chars",
            )
        )
        return int(used or 0)

    def _trainings_used(self, user_id: UUID, billing_month: str) -> int:
        used = self._session.scalar(
            select(func.count())
            .select_from(UsageRecordRow)
            .where(
                UsageRecordRow.user_id == user_id,
                UsageRecordRow.billing_month == billing_month,
                UsageRecordRow.record_type == "train",
            )
        )
        return int(used or 0)

    def _limits_for_user(self, user_id: UUID) -> tuple[int, int]:
        char_limit = self._settings.quota_monthly_char_limit
        train_limit = self._settings.quota_monthly_train_limit
        user = self._session.get(UserRow, user_id)
        if user:
            if user.quota_monthly_char_limit is not None:
                char_limit = user.quota_monthly_char_limit
            if user.quota_monthly_train_limit is not None:
                train_limit = user.quota_monthly_train_limit
        return char_limit, train_limit

    def get_summary(self, user_id: UUID) -> QuotaSummary:
        month = current_billing_month()
        char_limit, train_limit = self._limits_for_user(user_id)
        chars_used = self._chars_used(user_id, month)
        trainings_used = self._trainings_used(user_id, month)
        chars_remaining = max(0, char_limit - chars_used)
        wallet_balance = UserWalletRepository(self._session).get_balance(user_id)
        return QuotaSummary(
            monthly_char_limit=char_limit,
            chars_used=chars_used,
            chars_remaining=chars_remaining,
            wallet_token_balance=wallet_balance,
            total_tokens_remaining=chars_remaining + wallet_balance,
            monthly_train_limit=train_limit,
            trainings_used=trainings_used,
            trainings_remaining=max(0, train_limit - trainings_used),
            reset_at=next_reset_at(),
        )

    def ensure_chars_available(self, user_id: UUID, char_count: int) -> None:
        summary = self.get_summary(user_id)
        if char_count > summary.total_tokens_remaining:
            raise QuotaExceededError(
                quota_type="chars",
                message="TTS Token 不足，请购买 Token 包或等待下月重置",
                required=char_count,
                remaining=summary.total_tokens_remaining,
                monthly_limit=summary.monthly_char_limit,
                used=summary.chars_used,
                reset_at=summary.reset_at,
            )

    def ensure_training_available(self, user_id: UUID) -> None:
        summary = self.get_summary(user_id)
        if summary.trainings_remaining < 1:
            raise QuotaExceededError(
                quota_type="train",
                message="本月训练次数已达上限，请升级套餐或下月再试",
                required=1,
                remaining=summary.trainings_remaining,
                monthly_limit=summary.monthly_train_limit,
                used=summary.trainings_used,
                reset_at=summary.reset_at,
            )

    def record_chars(self, *, user_id: UUID, job_id: UUID, char_count: int) -> bool:
        month = current_billing_month()
        char_limit, _ = self._limits_for_user(user_id)
        chars_used_before = self._chars_used(user_id, month)
        remaining_monthly_before = max(0, char_limit - chars_used_before)
        wallet_portion = max(0, char_count - remaining_monthly_before)

        recorded = self._record(
            user_id=user_id,
            job_id=job_id,
            record_type="chars",
            amount=char_count,
        )
        if not recorded:
            return False
        if wallet_portion > 0:
            try:
                UserWalletRepository(self._session).debit_synthesis(
                    user_id=user_id,
                    job_id=job_id,
                    token_amount=wallet_portion,
                )
            except InsufficientWalletBalanceError:
                self._session.rollback()
                return False
        return True

    def record_training(self, *, user_id: UUID, job_id: UUID) -> bool:
        return self._record(
            user_id=user_id,
            job_id=job_id,
            record_type="train",
            amount=1,
        )

    def _record(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        record_type: str,
        amount: int,
    ) -> bool:
        row = UsageRecordRow(
            user_id=user_id,
            job_id=job_id,
            record_type=record_type,
            amount=amount,
            billing_month=current_billing_month(),
        )
        self._session.add(row)
        try:
            self._session.commit()
            return True
        except IntegrityError:
            self._session.rollback()
            return False

    def list_user_usage_report(
        self,
        *,
        billing_month: str | None = None,
        limit: int = 100,
    ) -> list[UserUsageReportRow]:
        month = billing_month or current_billing_month()
        usage_rows = self._session.execute(
            select(
                UsageRecordRow.user_id,
                UsageRecordRow.record_type,
                func.coalesce(func.sum(UsageRecordRow.amount), 0).label("total"),
            )
            .where(UsageRecordRow.billing_month == month)
            .group_by(UsageRecordRow.user_id, UsageRecordRow.record_type)
        ).all()

        by_user: dict[UUID, dict[str, int]] = {}
        for user_id, record_type, total in usage_rows:
            bucket = by_user.setdefault(user_id, {"chars": 0, "train": 0})
            if record_type == "chars":
                bucket["chars"] = int(total or 0)
            elif record_type == "train":
                bucket["train"] = int(total or 0)

        if not by_user:
            return []

        users = {
            row.id: row
            for row in self._session.scalars(select(UserRow).where(UserRow.id.in_(list(by_user.keys())))).all()
        }

        report: list[UserUsageReportRow] = []
        for user_id, stats in by_user.items():
            user = users.get(user_id)
            phone = user.phone if user else str(user_id).split("-")[0]
            char_limit, train_limit = self._limits_for_user(user_id)
            chars_used = stats["chars"]
            trainings_used = stats["train"]
            report.append(
                UserUsageReportRow(
                    user_id=str(user_id),
                    phone=phone,
                    chars_used=chars_used,
                    trainings_used=trainings_used,
                    monthly_char_limit=char_limit,
                    monthly_train_limit=train_limit,
                    chars_remaining=max(0, char_limit - chars_used),
                    trainings_remaining=max(0, train_limit - trainings_used),
                )
            )

        report.sort(key=lambda row: row.chars_used, reverse=True)
        return report[: max(1, min(limit, 500))]

    def set_user_limits(
        self,
        user_id: UUID,
        *,
        monthly_char_limit: int | None = None,
        monthly_train_limit: int | None = None,
    ) -> tuple[int, int]:
        user = self._session.get(UserRow, user_id)
        if not user:
            raise ValueError("USER_NOT_FOUND")
        if monthly_char_limit is not None:
            user.quota_monthly_char_limit = monthly_char_limit
        if monthly_train_limit is not None:
            user.quota_monthly_train_limit = monthly_train_limit
        self._session.commit()
        self._session.refresh(user)
        return self._limits_for_user(user_id)
