from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from domains.licensing.service import (
    catalog_entry_can_use,
    catalog_entry_purchased,
)
from voice_platform.auth.repository import UserRepository
from voice_platform.social.repository import UserProfileRepository
from voice_platform.social.system import send_system_notice
from domains.community.service import CommunityService
from voice_platform.config import get_settings
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import (
    JobRepository,
    VoiceAuthorizationRepository,
    VoiceCatalogRepository,
    VoiceGrantRepository,
    VoiceRepository,
    VoiceVersionRepository,
)
from voice_platform.job.schemas import (
    CatalogEntryResponse,
    CatalogPublishRequest,
    CreatorProfileResponse,
    InferPayload,
    JobStatus,
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
        self._auths = VoiceAuthorizationRepository(session)
        self._grants = VoiceGrantRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._voices = VoiceRepository(session)

    def _entry_response(
        self, entry, *, viewer_user_id: UUID | None = None, can_use: bool | None = None
    ) -> CatalogEntryResponse | None:
        self._sync_demo_from_job(entry)
        ver = self._versions.get(entry.voice_version_id)
        if not ver:
            return None
        voice = self._voices.get_voice(ver.voice_id)
        if can_use is None:
            can_use = (
                catalog_entry_can_use(self._session, entry, viewer_user_id)
                if viewer_user_id
                else entry.status == "published"
            )
        purchased = (
            catalog_entry_purchased(self._session, entry, viewer_user_id)
            if viewer_user_id
            else False
        )
        return CatalogEntryResponse(
            catalog_id=entry.id,
            voice_version_id=entry.voice_version_id,
            voice_id=ver.voice_id,
            voice_name=voice.name if voice else "unknown",
            title=entry.title,
            description=entry.description,
            tags=list(entry.tags_json or []),
            featured=entry.featured,
            status=entry.status,
            demo_text=entry.demo_text or "",
            demo_audio_url=entry.demo_audio_url,
            demo_job_id=entry.demo_job_id,
            owner_user_id=entry.owner_user_id,
            can_use=can_use,
            license_type=entry.license_type or "personal_non_commercial",
            price_cents=entry.price_cents or 0,
            billing_unit=entry.billing_unit or "per_1k_chars",
            included_chars=entry.included_chars or 0,
            prohibited_domains=list(entry.prohibited_domains_json or []),
            policy_version=entry.policy_version or 1,
            purchased=purchased,
        )

    def _sync_demo_from_job(self, entry) -> None:
        if entry.demo_audio_url or not entry.demo_job_id:
            return
        jobs = JobRepository(self._session)
        record = jobs.get_job(entry.demo_job_id)
        if not record or record.status != JobStatus.SUCCEEDED or not record.result:
            return
        url = record.result.get("audio_url")
        if not url:
            return
        self._catalog.set_demo_audio(entry.id, demo_audio_url=url)
        entry.demo_audio_url = url

    def _enqueue_catalog_demo(self, entry) -> None:
        settings = get_settings()
        text = (entry.demo_text or settings.catalog_demo_text).strip()
        if not text:
            return
        jobs = JobRepository(self._session)
        queue = RedisJobQueue()
        record = jobs.create_synthesize_job(
            owner_user_id=entry.owner_user_id,
            payload=InferPayload(
                voice_version_id=entry.voice_version_id,
                text=text,
                catalog_id=entry.id,
                skip_quota=True,
            ),
        )
        self._catalog.set_demo_job(entry.id, record.job_id)
        entry.demo_job_id = record.job_id
        queue.enqueue_infer(record.job_id)

    def list_catalog(
        self,
        *,
        user_id: UUID,
        featured_only: bool = False,
        tags: list[str] | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[CatalogEntryResponse]:
        _ = user_id
        out: list[CatalogEntryResponse] = []
        for entry in self._catalog.list_published(
            featured_only=featured_only,
            tags=tags,
            owner_user_id=owner_user_id,
        ):
            item = self._entry_response(entry, viewer_user_id=user_id)
            if item:
                out.append(item)
        return out

    @staticmethod
    def _mask_phone(phone: str) -> str:
        digits = phone.strip()
        if len(digits) >= 7:
            return f"{digits[:3]}****{digits[-4:]}"
        return "创作者"

    def get_creator_profile(
        self,
        *,
        owner_user_id: UUID,
        viewer_user_id: UUID,
        featured_only: bool = False,
        tags: list[str] | None = None,
    ) -> CreatorProfileResponse:
        _ = viewer_user_id
        user = UserRepository(self._session).get_by_id(owner_user_id)
        voices = self.list_catalog(
            user_id=viewer_user_id,
            featured_only=featured_only,
            tags=tags,
            owner_user_id=owner_user_id,
        )
        profile = UserProfileRepository(self._session).get(owner_user_id)
        bio = profile.bio if profile else ""
        if profile and profile.display_name:
            display_name = profile.display_name
        elif user:
            display_name = self._mask_phone(user.phone)
        else:
            short = str(owner_user_id).split("-")[0]
            display_name = f"创作者 · {short}"

        return CreatorProfileResponse(
            user_id=owner_user_id,
            display_name=display_name,
            bio=bio,
            published_count=len(voices),
            voices=voices,
        )

    def list_catalog_tags(self) -> list[str]:
        return self._catalog.list_distinct_tags()

    def list_my_submissions(self, *, owner_user_id: UUID) -> list[CatalogEntryResponse]:
        out: list[CatalogEntryResponse] = []
        for entry in self._catalog.list_for_owner(owner_user_id):
            item = self._entry_response(entry, viewer_user_id=owner_user_id)
            if item:
                out.append(item)
        return out

    def list_pending_review(self) -> list[CatalogEntryResponse]:
        out: list[CatalogEntryResponse] = []
        for entry in self._catalog.list_pending():
            item = self._entry_response(entry, can_use=False)
            if item:
                out.append(item)
        return out

    def publish_to_catalog(self, *, owner_user_id: UUID, body: CatalogPublishRequest) -> CatalogEntryResponse:
        ver = self._versions.get(body.voice_version_id)
        if not ver or ver.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        voice = self._voices.get_voice(ver.voice_id)
        if not voice:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        demo_text = body.demo_text.strip() or get_settings().catalog_demo_text
        entry = self._catalog.publish(
            voice_version_id=body.voice_version_id,
            owner_user_id=owner_user_id,
            title=body.title.strip(),
            description=body.description.strip(),
            tags=body.tags,
            featured=body.featured,
            demo_text=demo_text,
            license_type=body.license_type,
            price_cents=body.price_cents,
            billing_unit=body.billing_unit,
            included_chars=body.included_chars,
            prohibited_domains=body.prohibited_domains,
        )
        if get_settings().catalog_auto_approve:
            approved = self._catalog.approve(entry.id)
            entry = approved or entry
            if entry.status == "published":
                self._enqueue_catalog_demo(entry)
                CommunityService(self._session).record_catalog_published(
                    actor_user_id=owner_user_id,
                    catalog_id=entry.id,
                    title=entry.title,
                    price_cents=int(entry.price_cents or 0),
                )
        item = self._entry_response(entry, viewer_user_id=owner_user_id)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def approve_catalog_entry(self, *, catalog_id: UUID) -> CatalogEntryResponse:
        entry = self._catalog.approve(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Pending catalog entry not found", 404)
        self._enqueue_catalog_demo(entry)
        if entry.status == "published":
            CommunityService(self._session).record_catalog_published(
                actor_user_id=entry.owner_user_id,
                catalog_id=entry.id,
                title=entry.title,
                price_cents=int(entry.price_cents or 0),
            )
        item = self._entry_response(entry, can_use=False)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def regenerate_catalog_demo(self, *, catalog_id: UUID) -> CatalogEntryResponse:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Published catalog entry not found", 404)
        self._enqueue_catalog_demo(entry)
        item = self._entry_response(entry, can_use=True)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def reject_catalog_entry(self, *, catalog_id: UUID) -> CatalogEntryResponse:
        entry = self._catalog.reject(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Pending catalog entry not found", 404)
        item = self._entry_response(entry, can_use=False)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def unpublish_catalog_entry(self, *, catalog_id: UUID, owner_user_id: UUID) -> CatalogEntryResponse:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "发布记录不存在或无权操作", 404)
        if entry.status not in ("published", "pending"):
            raise MarketplaceServiceError(
                "INVALID_STATE",
                "当前状态无法下架，仅支持审核中或已上架条目",
                409,
            )
        self._catalog.takedown(catalog_id)
        self._auths.revoke_for_catalog(catalog_id)
        entry = self._catalog.get(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "发布记录不存在", 404)
        item = self._entry_response(entry, viewer_user_id=owner_user_id, can_use=False)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

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
        send_system_notice(
            self._session,
            recipient_user_id=body.grantee_user_id,
            conversation_peer_user_id=granter_user_id,
            body=f"【系统】你收到一条音色授权：{voice.name}（来自对方）。现在可以在工作台/音色馆直接使用。",
        )
        send_system_notice(
            self._session,
            recipient_user_id=granter_user_id,
            conversation_peer_user_id=body.grantee_user_id,
            body=f"【系统】你已向对方发放音色授权：{voice.name}。",
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

    def list_grants_issued(self, *, granter_user_id: UUID) -> list[VoiceGrantResponse]:
        now = datetime.now(timezone.utc)
        out: list[VoiceGrantResponse] = []
        for row in self._grants.list_for_granter(granter_user_id):
            if row.revoked_at:
                continue
            if row.expires_at and row.expires_at < now:
                continue
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
