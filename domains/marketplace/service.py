from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from domains.licensing.service import (
    catalog_entry_can_use,
    catalog_entry_purchased,
)
from voice_platform.auth.identifiers import mask_email
from voice_platform.auth.repository import UserRepository
from voice_platform.social.repository import UserProfileRepository
from voice_platform.social.system import send_system_notice
from domains.community.service import CommunityService
from voice_platform.config import get_settings
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import (
    JobRepository,
    QualityReportRepository,
    VoiceAuthorizationRepository,
    VoiceCatalogRepository,
    VoiceGrantRepository,
    VoiceRepository,
    VoiceVersionRepository,
)
from voice_platform.job.schemas import (
    CatalogCoverGenerateRequest,
    CatalogCoverGenerateResponse,
    CatalogCoverUploadResponse,
    CatalogEntryResponse,
    CatalogEntryUpdateRequest,
    CatalogPublishRequest,
    CreatorProfileResponse,
    FeaturedCreatorSummary,
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

    @staticmethod
    def _resolve_entry_cover(entry) -> str:
        from domains.marketplace.avatar_defaults import resolve_catalog_cover_url

        return resolve_catalog_cover_url(
            tags=list(entry.tags_json or []),
            cover_image_url=entry.cover_image_url,
        )

    @staticmethod
    def _normalize_cover_url(url: str | None) -> str | None:
        if not url:
            return url
        text = url.strip()
        for prefix in (
            "http://localhost:8001",
            "http://127.0.0.1:8001",
            "https://localhost:8001",
            "https://127.0.0.1:8001",
        ):
            if text.startswith(prefix):
                path = text[len(prefix) :]
                return path if path.startswith("/") else f"/{path}"
        return text

    def _resolve_owner_display_name(
        self, owner_user_id: UUID, cache: dict[UUID, str] | None = None
    ) -> str:
        if cache is not None and owner_user_id in cache:
            return cache[owner_user_id]
        profile = UserProfileRepository(self._session).get(owner_user_id)
        if profile and profile.display_name:
            name = profile.display_name
        else:
            user = UserRepository(self._session).get_by_id(owner_user_id)
            if user:
                if user.phone:
                    name = self._mask_phone(user.phone)
                elif user.email:
                    name = mask_email(user.email)
                else:
                    name = f"创作者 · {str(owner_user_id).split('-')[0]}"
            else:
                short = str(owner_user_id).split("-")[0]
                name = f"创作者 · {short}"
        if cache is not None:
            cache[owner_user_id] = name
        return name

    def _entry_response(
        self,
        entry,
        *,
        viewer_user_id: UUID | None = None,
        can_use: bool | None = None,
        owner_names: dict[UUID, str] | None = None,
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
            cover_image_url=self._normalize_cover_url(self._resolve_entry_cover(entry)),
            owner_user_id=entry.owner_user_id,
            owner_display_name=self._resolve_owner_display_name(entry.owner_user_id, owner_names),
            can_use=can_use,
            license_type=entry.license_type or "personal_non_commercial",
            price_cents=entry.price_cents or 0,
            billing_unit=entry.billing_unit or "per_1k_chars",
            included_chars=entry.included_chars or 0,
            prohibited_domains=list(entry.prohibited_domains_json or []),
            policy_version=entry.policy_version or 1,
            purchased=purchased,
            quality_pass=self._quality_pass_for_version(ver.id),
            similarity_score=self._similarity_for_version(ver.id),
        )

    def _quality_pass_for_version(self, voice_version_id: UUID) -> bool | None:
        report = QualityReportRepository(self._session).get(voice_version_id)
        return report.quality_pass if report else None

    def _similarity_for_version(self, voice_version_id: UUID) -> float | None:
        report = QualityReportRepository(self._session).get(voice_version_id)
        return report.similarity_score if report else None

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
        owner_names: dict[UUID, str] = {}
        for entry in self._catalog.list_published(
            featured_only=featured_only,
            tags=tags,
            owner_user_id=owner_user_id,
        ):
            item = self._entry_response(
                entry, viewer_user_id=user_id, owner_names=owner_names
            )
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
        voices = self.list_catalog(
            user_id=viewer_user_id,
            featured_only=featured_only,
            tags=tags,
            owner_user_id=owner_user_id,
        )
        profile = UserProfileRepository(self._session).get(owner_user_id)
        bio = profile.bio if profile else ""
        from domains.marketplace.avatar_defaults import resolve_creator_avatar_url

        avatar_url = resolve_creator_avatar_url(
            user_id=owner_user_id,
            avatar_url=profile.avatar_url if profile else None,
        )
        display_name = self._resolve_owner_display_name(owner_user_id)

        return CreatorProfileResponse(
            user_id=owner_user_id,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
            published_count=len(voices),
            voices=voices,
        )

    def list_featured_creators(
        self,
        *,
        viewer_user_id: UUID,
        limit: int = 12,
    ) -> list[FeaturedCreatorSummary]:
        featured_entries = self.list_catalog(
            user_id=viewer_user_id,
            featured_only=True,
        )
        grouped: dict[UUID, list[CatalogEntryResponse]] = {}
        for entry in featured_entries:
            grouped.setdefault(entry.owner_user_id, []).append(entry)

        out: list[FeaturedCreatorSummary] = []
        for owner_id, voices in grouped.items():
            profile = self.get_creator_profile(
                owner_user_id=owner_id,
                viewer_user_id=viewer_user_id,
            )
            spotlight = next((v for v in voices if v.demo_audio_url), voices[0] if voices else None)
            out.append(
                FeaturedCreatorSummary(
                    user_id=owner_id,
                    display_name=profile.display_name,
                    bio=profile.bio,
                    avatar_url=profile.avatar_url,
                    published_count=profile.published_count,
                    featured_voice_count=len(voices),
                    spotlight_voice=spotlight,
                )
            )

        out.sort(
            key=lambda item: (item.featured_voice_count, item.published_count, item.display_name),
            reverse=True,
        )
        return out[: max(1, min(limit, 50))]

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
        from domains.marketplace.invite_service import (
            MarketplaceInviteService,
            MarketplaceInviteServiceError,
        )

        invite_svc = MarketplaceInviteService(self._session)
        try:
            invite_svc.ensure_can_publish(user_id=owner_user_id)
            invite_svc.ensure_quality_pass(voice_version_id=body.voice_version_id)
        except MarketplaceInviteServiceError as exc:
            raise MarketplaceServiceError(exc.code, exc.message, exc.http_status) from exc

        ver = self._versions.get(body.voice_version_id)
        if not ver or ver.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        voice = self._voices.get_voice(ver.voice_id)
        if not voice:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        demo_text = body.demo_text.strip() or get_settings().catalog_demo_text
        cover_url = self._normalize_cover_url((body.cover_image_url.strip() or None))
        if not cover_url:
            from domains.marketplace.avatar_defaults import default_catalog_cover_url

            cover_url = default_catalog_cover_url(body.tags)
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
            cover_image_url=cover_url,
        )
        from domains.marketplace.avatar_assign import AvatarAssignService

        AvatarAssignService(self._session).ensure_creator_avatar(owner_user_id)
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

    def generate_catalog_cover_preview(
        self, *, owner_user_id: UUID, body: CatalogCoverGenerateRequest
    ) -> CatalogCoverGenerateResponse:
        from domains.marketplace.cover_image import CatalogCoverError, generate_and_store_catalog_cover

        try:
            url, prompt = generate_and_store_catalog_cover(
                owner_user_id=owner_user_id,
                title=body.title.strip(),
                tags=body.tags,
                prompt=body.prompt,
            )
        except CatalogCoverError as exc:
            raise MarketplaceServiceError(exc.code, exc.message, exc.http_status) from exc
        return CatalogCoverGenerateResponse(
            cover_image_url=self._normalize_cover_url(url) or url,
            prompt=prompt,
        )

    def generate_catalog_cover_for_entry(
        self,
        *,
        catalog_id: UUID,
        owner_user_id: UUID,
        body: CatalogCoverGenerateRequest | None = None,
    ) -> CatalogEntryResponse:
        from domains.marketplace.cover_image import CatalogCoverError, generate_and_store_catalog_cover

        entry = self._catalog.get(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Catalog entry not found", 404)
        if entry.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("FORBIDDEN", "Only the owner can generate cover", 403)
        title = body.title.strip() if body and body.title.strip() else entry.title
        tags = body.tags if body and body.tags else list(entry.tags_json or [])
        prompt = body.prompt if body else None
        try:
            url, _prompt = generate_and_store_catalog_cover(
                owner_user_id=owner_user_id,
                title=title,
                tags=tags,
                catalog_id=catalog_id,
                prompt=prompt,
            )
        except CatalogCoverError as exc:
            raise MarketplaceServiceError(exc.code, exc.message, exc.http_status) from exc
        normalized = self._normalize_cover_url(url) or url
        updated = self._catalog.set_cover_image_url(catalog_id, cover_image_url=normalized)
        entry = updated or entry
        item = self._entry_response(entry, viewer_user_id=owner_user_id)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def upload_catalog_cover_draft(
        self, *, owner_user_id: UUID, data: bytes, filename: str
    ) -> CatalogCoverUploadResponse:
        from domains.marketplace.cover_image import CatalogCoverError, upload_and_store_catalog_cover

        ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
        try:
            url = upload_and_store_catalog_cover(
                owner_user_id=owner_user_id,
                data=data,
                ext=ext,
            )
        except CatalogCoverError as exc:
            raise MarketplaceServiceError(exc.code, exc.message, exc.http_status) from exc
        return CatalogCoverUploadResponse(cover_image_url=self._normalize_cover_url(url) or url)

    def upload_catalog_cover_for_entry(
        self, *, catalog_id: UUID, owner_user_id: UUID, data: bytes, filename: str
    ) -> CatalogEntryResponse:
        from domains.marketplace.cover_image import CatalogCoverError, upload_and_store_catalog_cover

        entry = self._catalog.get(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Catalog entry not found", 404)
        if entry.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("FORBIDDEN", "Only the owner can upload cover", 403)
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
        try:
            url = upload_and_store_catalog_cover(
                owner_user_id=owner_user_id,
                data=data,
                ext=ext,
                catalog_id=catalog_id,
            )
        except CatalogCoverError as exc:
            raise MarketplaceServiceError(exc.code, exc.message, exc.http_status) from exc
        normalized = self._normalize_cover_url(url) or url
        updated = self._catalog.set_cover_image_url(catalog_id, cover_image_url=normalized)
        entry = updated or entry
        item = self._entry_response(entry, viewer_user_id=owner_user_id)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def update_catalog_entry(
        self, *, catalog_id: UUID, owner_user_id: UUID, body: CatalogEntryUpdateRequest
    ) -> CatalogEntryResponse:
        entry = self._catalog.get(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Catalog entry not found", 404)
        if entry.owner_user_id != owner_user_id:
            raise MarketplaceServiceError("FORBIDDEN", "Only the owner can update entry", 403)

        tags = body.tags
        if tags is not None and len(tags) > 10:
            raise MarketplaceServiceError("INVALID_TAGS", "标签不能超过 10 个", 400)

        cover_url = body.cover_image_url
        if cover_url is not None:
            cover_url = self._normalize_cover_url(cover_url.strip() or None)

        updated = self._catalog.update_owner_entry(
            catalog_id,
            owner_user_id,
            title=body.title.strip() if body.title else None,
            description=body.description if body.description is not None else None,
            tags=tags,
            cover_image_url=cover_url,
        )
        if not updated:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Catalog entry not found", 404)
        item = self._entry_response(updated, viewer_user_id=owner_user_id)
        if not item:
            raise MarketplaceServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def approve_catalog_entry(self, *, catalog_id: UUID) -> CatalogEntryResponse:
        entry = self._catalog.approve(catalog_id)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Pending catalog entry not found", 404)
        from domains.marketplace.avatar_assign import AvatarAssignService

        assigner = AvatarAssignService(self._session)
        assigner.ensure_catalog_cover(entry)
        assigner.ensure_creator_avatar(entry.owner_user_id)
        entry = self._catalog.get(catalog_id) or entry
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

    def reject_catalog_entry(self, *, catalog_id: UUID, reason: str) -> CatalogEntryResponse:
        from voice_platform.social.system import send_system_notice

        entry = self._catalog.reject(catalog_id, reason=reason)
        if not entry:
            raise MarketplaceServiceError("CATALOG_NOT_FOUND", "Pending catalog entry not found", 404)
        send_system_notice(
            self._session,
            recipient_user_id=entry.owner_user_id,
            conversation_peer_user_id=entry.owner_user_id,
            body=f"【系统】你的音色馆上架申请「{entry.title}」未通过审核。原因：{reason.strip()}",
        )
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
