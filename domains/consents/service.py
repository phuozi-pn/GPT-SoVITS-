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

    def list_pending(self) -> list:
        from voice_platform.job.schemas import ConsentAdminSummary

        rows = self._voices.list_pending_consents()
        out: list[ConsentAdminSummary] = []
        for row in rows:
            voice = self._voices.get_voice(row.voice_id)
            out.append(
                ConsentAdminSummary(
                    consent_id=row.id,
                    voice_id=row.voice_id,
                    owner_user_id=row.owner_user_id,
                    voice_name=voice.name if voice else "unknown",
                    status=row.status,
                    created_at=row.created_at,
                    approved_at=row.approved_at,
                    reject_reason=row.reject_reason,
                )
            )
        return out

    def approve(self, *, consent_id: UUID, admin_user_id: UUID):
        from voice_platform.job.schemas import ConsentAdminSummary

        row = self._voices.update_consent_review(
            consent_id=consent_id,
            status="approved",
            reviewed_by=admin_user_id,
        )
        if not row:
            raise ConsentServiceError("NOT_FOUND", "Consent not found", 404)
        voice = self._voices.get_voice(row.voice_id)
        return ConsentAdminSummary(
            consent_id=row.id,
            voice_id=row.voice_id,
            owner_user_id=row.owner_user_id,
            voice_name=voice.name if voice else "unknown",
            status=row.status,
            created_at=row.created_at,
            approved_at=row.approved_at,
            reject_reason=row.reject_reason,
        )

    def reject(self, *, consent_id: UUID, admin_user_id: UUID, reason: str):
        from voice_platform.job.schemas import ConsentAdminSummary
        from voice_platform.social.system import send_system_notice

        row = self._voices.update_consent_review(
            consent_id=consent_id,
            status="rejected",
            reviewed_by=admin_user_id,
            reject_reason=reason.strip(),
        )
        if not row:
            raise ConsentServiceError("NOT_FOUND", "Consent not found", 404)
        voice = self._voices.get_voice(row.voice_id)
        send_system_notice(
            self._session,
            recipient_user_id=row.owner_user_id,
            conversation_peer_user_id=row.owner_user_id,
            body=f"【系统】你的声纹授权书未通过审核。原因：{reason.strip()}",
        )
        return ConsentAdminSummary(
            consent_id=row.id,
            voice_id=row.voice_id,
            owner_user_id=row.owner_user_id,
            voice_name=voice.name if voice else "unknown",
            status=row.status,
            created_at=row.created_at,
            approved_at=row.approved_at,
            reject_reason=row.reject_reason,
        )
