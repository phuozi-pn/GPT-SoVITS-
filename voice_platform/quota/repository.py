from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from voice_platform.config import get_settings
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.models import UsageRecordRow
from voice_platform.quota.period import current_billing_month, next_reset_at
from voice_platform.quota.schemas import QuotaSummary


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

    def get_summary(self, user_id: UUID) -> QuotaSummary:
        month = current_billing_month()
        char_limit = self._settings.quota_monthly_char_limit
        train_limit = self._settings.quota_monthly_train_limit
        chars_used = self._chars_used(user_id, month)
        trainings_used = self._trainings_used(user_id, month)
        return QuotaSummary(
            monthly_char_limit=char_limit,
            chars_used=chars_used,
            chars_remaining=max(0, char_limit - chars_used),
            monthly_train_limit=train_limit,
            trainings_used=trainings_used,
            trainings_remaining=max(0, train_limit - trainings_used),
            reset_at=next_reset_at(),
        )

    def ensure_chars_available(self, user_id: UUID, char_count: int) -> None:
        summary = self.get_summary(user_id)
        if char_count > summary.chars_remaining:
            raise QuotaExceededError(
                quota_type="chars",
                message="本月合成字符额度不足，请升级套餐或下月再试",
                required=char_count,
                remaining=summary.chars_remaining,
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
        return self._record(
            user_id=user_id,
            job_id=job_id,
            record_type="chars",
            amount=char_count,
        )

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
