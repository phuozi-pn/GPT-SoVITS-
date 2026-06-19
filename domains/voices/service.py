from __future__ import annotations

from uuid import UUID

from domains.voices.access import list_accessible_version_ids
from voice_platform.job.repository import (
    ProjectRepository,
    VoiceCatalogRepository,
    VoiceRepository,
    VoiceVersionRepository,
)
from voice_platform.job.schemas import (
    VoiceCreateResponse,
    VoiceSummary,
    VoiceAssetManageSummary,
    VoiceConsentManageSummary,
    VoiceVersionManageSummary,
    VoiceVersionSummary,
)


class VoiceServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


_BLOCKED_CATALOG_STATUSES = frozenset({"pending", "published"})
_UNPUBLISH_CATALOG_STATUSES = frozenset({"pending", "published"})


class VoiceService:
    def __init__(self, session) -> None:
        self._session = session
        self._voices = VoiceRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._catalog = VoiceCatalogRepository(session)
        self._projects = ProjectRepository(session)

    def create(self, *, owner_user_id: UUID, name: str) -> VoiceCreateResponse:
        row = self._voices.create_voice(owner_user_id=owner_user_id, name=name)
        return VoiceCreateResponse(voice_id=row.id, name=row.name)

    def _version_summary(
        self,
        row,
        *,
        voice_name: str,
        granted: bool = False,
        manage: bool = False,
    ) -> VoiceVersionSummary | VoiceVersionManageSummary:
        meta = row.metadata_json or {}
        base = VoiceVersionSummary(
            voice_version_id=row.id,
            voice_id=row.voice_id,
            voice_name=voice_name,
            version=row.version,
            model_tag=row.model_tag,
            label=meta.get("label"),
            ref_text=row.ref_text,
            imported=bool(meta.get("imported")),
            granted=granted,
            created_at=row.created_at,
        )
        if not manage:
            return base

        catalog = self._catalog.find_by_version(row.id)
        can_delete, block_reason = self._delete_constraints(row.id, catalog)
        can_unpublish = bool(catalog and catalog.status in _UNPUBLISH_CATALOG_STATUSES)
        return VoiceVersionManageSummary(
            **base.model_dump(),
            catalog_id=catalog.id if catalog else None,
            catalog_status=catalog.status if catalog else None,
            catalog_title=catalog.title if catalog else None,
            can_unpublish=can_unpublish,
            can_delete=can_delete,
            delete_block_reason=block_reason,
        )

    def _asset_summary(self, row) -> VoiceAssetManageSummary:
        qc = row.qc_result_json or {}
        return VoiceAssetManageSummary(
            asset_id=row.id,
            voice_id=row.voice_id,
            storage_uri=row.storage_uri,
            locked=bool(row.locked),
            qc_passed=bool(row.qc_passed),
            qc_status=qc.get("status"),
            duration_sec=qc.get("duration_sec"),
            created_at=row.created_at,
        )

    def _consent_summary(self, row) -> VoiceConsentManageSummary:
        return VoiceConsentManageSummary(
            consent_id=row.id,
            voice_id=row.voice_id,
            status=row.status,
            approved_at=row.approved_at,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    def _delete_constraints(self, voice_version_id: UUID, catalog) -> tuple[bool, str | None]:
        if catalog and catalog.status in _BLOCKED_CATALOG_STATUSES:
            label = "已上架" if catalog.status == "published" else "审核中"
            return False, f"该版本在音色馆{label}，请先在下方点击「下架」后再删除"
        if self._projects.version_in_use(voice_version_id):
            return False, "该版本已绑定到批量配音项目角色"
        return True, None

    def list_voices(self, owner_user_id: UUID, *, detail: bool = False) -> list[VoiceSummary]:
        out: list[VoiceSummary] = []
        for v in self._voices.list_voices(owner_user_id):
            version_rows = self._versions.list_for_voice(v.id, owner_user_id)
            versions = None
            assets = None
            consents = None
            if detail:
                versions = [
                    self._version_summary(
                        row,
                        voice_name=v.name,
                        granted=False,
                        manage=True,
                    )
                    for row in version_rows
                ]
                assets = [
                    self._asset_summary(row)
                    for row in self._voices.list_assets_for_voice(v.id, owner_user_id)
                ]
                consents = [
                    self._consent_summary(row)
                    for row in self._voices.list_consents_for_voice(v.id, owner_user_id)
                ]
            out.append(
                VoiceSummary(
                    voice_id=v.id,
                    name=v.name,
                    version_count=len(version_rows),
                    latest_version_id=version_rows[0].id if version_rows else None,
                    versions=versions,
                    assets=assets,
                    consents=consents,
                )
            )
        return out

    def list_versions(self, owner_user_id: UUID) -> list[VoiceVersionSummary]:
        voice_names = {v.id: v.name for v in self._voices.list_voices(owner_user_id)}
        out: list[VoiceVersionSummary] = []
        seen: set[UUID] = set()
        for row in self._versions.list_for_user(owner_user_id):
            seen.add(row.id)
            out.append(
                self._version_summary(
                    row,
                    voice_name=voice_names.get(row.voice_id, "音色"),
                    granted=False,
                )
            )
        for version_id in list_accessible_version_ids(self._session, owner_user_id):
            if version_id in seen:
                continue
            row = self._versions.get(version_id)
            if not row:
                continue
            voice = self._voices.get_voice(row.voice_id)
            out.append(
                self._version_summary(
                    row,
                    voice_name=voice.name if voice else "音色",
                    granted=True,
                )
            )
        return out

    def update_voice_name(self, *, voice_id: UUID, owner_user_id: UUID, name: str) -> VoiceSummary:
        row = self._voices.update_name(voice_id=voice_id, owner_user_id=owner_user_id, name=name)
        if not row:
            raise VoiceServiceError("VOICE_NOT_FOUND", "音色不存在或无权修改", 404)
        versions = self._versions.list_for_voice(voice_id, owner_user_id)
        return VoiceSummary(
            voice_id=row.id,
            name=row.name,
            version_count=len(versions),
            latest_version_id=versions[0].id if versions else None,
        )

    def update_version(
        self,
        *,
        voice_version_id: UUID,
        owner_user_id: UUID,
        label: str | None = None,
        ref_text: str | None = None,
    ) -> VoiceVersionSummary:
        row = self._versions.update_metadata(
            voice_version_id,
            owner_user_id=owner_user_id,
            label=label,
            ref_text=ref_text,
        )
        if not row:
            raise VoiceServiceError("VERSION_NOT_FOUND", "音色版本不存在或无权修改", 404)
        voice = self._voices.get_voice(row.voice_id)
        return self._version_summary(
            row,
            voice_name=voice.name if voice else "音色",
            granted=False,
        )

    def delete_version(self, *, voice_version_id: UUID, owner_user_id: UUID) -> None:
        row = self._versions.get(voice_version_id)
        if not row or row.owner_user_id != owner_user_id:
            raise VoiceServiceError("VERSION_NOT_FOUND", "音色版本不存在或无权删除", 404)
        catalog = self._catalog.find_by_version(voice_version_id)
        can_delete, block_reason = self._delete_constraints(voice_version_id, catalog)
        if not can_delete:
            raise VoiceServiceError("VERSION_IN_USE", block_reason or "无法删除", 409)
        self._versions.delete_version(voice_version_id)

    def delete_voice(self, *, voice_id: UUID, owner_user_id: UUID) -> None:
        voice = self._voices.get_voice(voice_id)
        if not voice or voice.owner_user_id != owner_user_id:
            raise VoiceServiceError("VOICE_NOT_FOUND", "音色不存在或无权删除", 404)
        versions = self._versions.list_for_voice(voice_id, owner_user_id)
        for ver in versions:
            catalog = self._catalog.find_by_version(ver.id)
            can_delete, block_reason = self._delete_constraints(ver.id, catalog)
            if not can_delete:
                raise VoiceServiceError(
                    "VOICE_IN_USE",
                    block_reason or "音色含有不可删除的版本",
                    409,
                )
        self._voices.delete_voice_tree(voice_id)
