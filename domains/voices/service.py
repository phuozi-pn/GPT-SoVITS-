from __future__ import annotations

from uuid import UUID

from voice_platform.job.repository import VoiceRepository, VoiceVersionRepository
from voice_platform.job.schemas import VoiceCreateResponse, VoiceSummary, VoiceVersionSummary


class VoiceServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class VoiceService:
    def __init__(self, session) -> None:
        self._voices = VoiceRepository(session)
        self._versions = VoiceVersionRepository(session)

    def create(self, *, owner_user_id: UUID, name: str) -> VoiceCreateResponse:
        row = self._voices.create_voice(owner_user_id=owner_user_id, name=name)
        return VoiceCreateResponse(voice_id=row.id, name=row.name)

    def list_voices(self, owner_user_id: UUID) -> list[VoiceSummary]:
        out: list[VoiceSummary] = []
        for v in self._voices.list_voices(owner_user_id):
            versions = self._versions.list_for_voice(v.id, owner_user_id)
            out.append(
                VoiceSummary(
                    voice_id=v.id,
                    name=v.name,
                    version_count=len(versions),
                    latest_version_id=versions[0].id if versions else None,
                )
            )
        return out

    def list_versions(self, owner_user_id: UUID) -> list[VoiceVersionSummary]:
        voice_names = {v.id: v.name for v in self._voices.list_voices(owner_user_id)}
        out: list[VoiceVersionSummary] = []
        for row in self._versions.list_for_user(owner_user_id):
            meta = row.metadata_json or {}
            out.append(
                VoiceVersionSummary(
                    voice_version_id=row.id,
                    voice_id=row.voice_id,
                    voice_name=voice_names.get(row.voice_id, "音色"),
                    version=row.version,
                    model_tag=row.model_tag,
                    label=meta.get("label"),
                    ref_text=row.ref_text,
                    imported=bool(meta.get("imported")),
                    created_at=row.created_at,
                )
            )
        return out
