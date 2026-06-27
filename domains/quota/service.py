"""Platform quota domain service — wraps QuotaRepository for routes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.repository import QuotaRepository
from voice_platform.quota.schemas import QuotaSummary


class QuotaServiceError(Exception):
    """Domain-level quota error with code, message, http_status, and optional details."""

    def __init__(self, code: str, message: str, http_status: int = 402, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)


class QuotaService:
    """Monthly usage quota use cases — chars & training limits."""

    def __init__(self, session: Session) -> None:
        self._repo = QuotaRepository(session)

    def get_summary(self, user_id: UUID) -> QuotaSummary:
        """Get the current user's quota summary."""
        return self._repo.get_summary(user_id)

    def list_usage_report(self, *, billing_month: str | None = None, limit: int = 100):
        return self._repo.list_user_usage_report(billing_month=billing_month, limit=limit)

    def ensure_chars_available(self, user_id: UUID, char_count: int) -> None:
        """Raise QuotaServiceError if not enough chars remain this month."""
        try:
            self._repo.ensure_chars_available(user_id, char_count)
        except QuotaExceededError as exc:
            raise QuotaServiceError("QUOTA_EXCEEDED", exc.message, 402, details=exc.to_detail()["details"]) from exc

    def ensure_training_available(self, user_id: UUID) -> None:
        """Raise QuotaServiceError if no training slots remain this month."""
        try:
            self._repo.ensure_training_available(user_id)
        except QuotaExceededError as exc:
            raise QuotaServiceError("QUOTA_EXCEEDED", exc.message, 402, details=exc.to_detail()["details"]) from exc

    def set_user_limits(
        self,
        user_id: UUID,
        *,
        monthly_char_limit: int | None = None,
        monthly_train_limit: int | None = None,
    ) -> QuotaSummary:
        try:
            self._repo.set_user_limits(
                user_id,
                monthly_char_limit=monthly_char_limit,
                monthly_train_limit=monthly_train_limit,
            )
        except ValueError as exc:
            if str(exc) == "USER_NOT_FOUND":
                raise QuotaServiceError("USER_NOT_FOUND", "用户不存在", 404) from exc
            raise
        return self._repo.get_summary(user_id)

    def record_training(self, *, user_id: UUID, job_id: UUID) -> bool:
        """Record one successful training/import against monthly train quota."""
        return self._repo.record_training(user_id=user_id, job_id=job_id)
