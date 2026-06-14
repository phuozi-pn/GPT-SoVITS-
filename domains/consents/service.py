from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.job.repository import VoiceRepository
from voice_platform.job.schemas import ConsentCreateResponse


class ConsentServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class ConsentService:
    def __init__(self, session) -> None:
        self._voices = VoiceRepository(session)

    def create(self, *, owner_user_id: UUID, voice_id: UUID) -> ConsentCreateResponse:
        if not self._voices.user_owns_voice(voice_id, owner_user_id):
            raise ConsentServiceError("FORBIDDEN", "Voice not accessible", 403)

        settings = get_settings()
        approved_at = datetime.now(timezone.utc) if settings.consent_auto_approve else None
        status = "approved" if settings.consent_auto_approve else "pending"
        row = self._voices.create_consent(
            owner_user_id=owner_user_id,
            voice_id=voice_id,
            status=status,
            approved_at=approved_at,
        )
        return ConsentCreateResponse(
            consent_id=row.id,
            voice_id=voice_id,
            status=row.status,
        )
