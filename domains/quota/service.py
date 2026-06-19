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
