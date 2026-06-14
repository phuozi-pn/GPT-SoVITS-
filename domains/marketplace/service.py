from __future__ import annotations

from uuid import UUID

from voice_platform.job.repository import (
    VoiceCatalogRepository,
    VoiceGrantRepository,
    VoiceRepository,
    VoiceVersionRepository,
)
from voice_platform.job.schemas import (
    CatalogEntryResponse,
    CatalogPublishRequest,
    VoiceGrantCreateRequest,
    VoiceGrantResponse,
)


class MarketplaceServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class MarketplaceService:
    def __init__(self, session) -> None:
        self._session = session
        self._catalog = VoiceCatalogRepository(session)
        self._grants = VoiceGrantRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._voices = VoiceRepository(session)

    def list_catalog(self, *, user_id: UUID, featured_only: bool = False) -> list[CatalogEntryResponse]:
        out: list[CatalogEntryResponse] = []
        for entry in self._catalog.list_published(featured_only=featured_only):
            ver = self._versions.get(entry.voice_version_id)
            if not ver:
                continue
            voice = self._voices.get_voice(ver.voice_id)
            out.append(
                CatalogEntryResponse(
                    catalog_id=entry.id,
                    voice_version_id=entry.voice_version_id,
                    voice_id=ver.voice_id,
                    voice_name=voice.name if voice else "unknown",
                    title=entry.title,
                    description=entry.description,
                    tags=list(entry.tags_json or []),
                    featured=entry.featured,
                    owner_user_id=entry.owner_user_id,
                    can_use=True,
                )
            )
        return out

    def publish_to_catalog(self, *, owner_user_id: UUID, body: CatalogPublishRequest) -> CatalogEntryResponse:
        ver = self._versions.get(body.voice_version_id)
        if not ver or ver.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        voice = self._voices.get_voice(ver.voice_id)
        if not voice:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        entry = self._catalog.publish(
            voice_version_id=body.voice_version_id,
            owner_user_id=owner_user_id,
            title=body.title.strip(),
            description=body.description.strip(),
            tags=body.tags,
            featured=body.featured,
        )
        return CatalogEntryResponse(
            catalog_id=entry.id,
            voice_version_id=entry.voice_version_id,
            voice_id=ver.voice_id,
            voice_name=voice.name,
            title=entry.title,
            description=entry.description,
            tags=list(entry.tags_json or []),
            featured=entry.featured,
            owner_user_id=entry.owner_user_id,
            can_use=True,
        )

    def create_grant(
        self,
        *,
        voice_id: UUID,
        granter_user_id: UUID,
        body: VoiceGrantCreateRequest,
    ) -> VoiceGrantResponse:
        voice = self._voices.get_voice(voice_id)
        if not voice or voice.owner_user_id != granter_user_id:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        if body.grantee_user_id == granter_user_id:
            raise MarketplaceServiceError("INVALID_GRANTEE", "Cannot grant to yourself", 400)
        row = self._grants.create_grant(
            voice_id=voice_id,
            granter_user_id=granter_user_id,
            grantee_user_id=body.grantee_user_id,
            expires_at=body.expires_at,
        )
        return VoiceGrantResponse(
            grant_id=row.id,
            voice_id=row.voice_id,
            voice_name=voice.name,
            granter_user_id=row.granter_user_id,
            grantee_user_id=row.grantee_user_id,
            scope=row.scope,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    def list_grants_received(self, *, grantee_user_id: UUID) -> list[VoiceGrantResponse]:
        out: list[VoiceGrantResponse] = []
        for row in self._grants.list_active_for_grantee(grantee_user_id):
            voice = self._voices.get_voice(row.voice_id)
            out.append(
                VoiceGrantResponse(
                    grant_id=row.id,
                    voice_id=row.voice_id,
                    voice_name=voice.name if voice else "unknown",
                    granter_user_id=row.granter_user_id,
                    grantee_user_id=row.grantee_user_id,
                    scope=row.scope,
                    expires_at=row.expires_at,
                    created_at=row.created_at,
                )
            )
        return out

    def revoke_grant(self, *, grant_id: UUID, granter_user_id: UUID) -> None:
        if not self._grants.revoke(grant_id, granter_user_id):
            raise MarketplaceServiceError("GRANT_NOT_FOUND", "Grant not found", 404)
