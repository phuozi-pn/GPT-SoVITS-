from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

from domains.licensing.service import catalog_entry_can_use
from voice_platform.auth.repository import UserRepository
from voice_platform.job.repository import VoiceCatalogRepository
from voice_platform.social.repository import (
    UserMessageRepository,
    UserProfileRepository,
    VoiceDownloadEventRepository,
)
from voice_platform.social.schemas import (
    ConversationPreviewResponse,
    MessageCreateRequest,
    MessageResponse,
    UserDirectoryEntry,
    UserProfileUpdateRequest,
    UserPublicProfileResponse,
)
from voice_platform.storage.local import LocalStorage


class SocialServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class SocialService:
    def __init__(self, session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._profiles = UserProfileRepository(session)
        self._messages = UserMessageRepository(session)
        self._catalog = VoiceCatalogRepository(session)
        self._downloads = VoiceDownloadEventRepository(session)

    @staticmethod
    def _mask_phone(phone: str) -> str:
        digits = phone.strip()
        if len(digits) >= 7:
            return f"{digits[:3]}****{digits[-4:]}"
        return "用户"

    def _display_name(self, user_id: UUID) -> str:
        profile = self._profiles.get(user_id)
        if profile and profile.display_name:
            return profile.display_name
        user = self._users.get_by_id(user_id)
        if user:
            return self._mask_phone(user.phone)
        return f"用户 · {str(user_id).split('-')[0]}"

    def _published_count(self, user_id: UUID) -> int:
        return len(self._catalog.list_published(owner_user_id=user_id))

    def _profile_response(self, user_id: UUID, *, viewer_user_id: UUID) -> UserPublicProfileResponse:
        profile = self._profiles.get(user_id)
        if profile and not profile.is_public and viewer_user_id != user_id:
            raise SocialServiceError("PROFILE_PRIVATE", "该用户主页未公开", 403)
        user = self._users.get_by_id(user_id)
        if not user and viewer_user_id != user_id:
            raise SocialServiceError("USER_NOT_FOUND", "用户不存在", 404)
        bio = profile.bio if profile else ""
        return UserPublicProfileResponse(
            user_id=user_id,
            display_name=self._display_name(user_id),
            bio=bio,
            published_voice_count=self._published_count(user_id),
            is_self=viewer_user_id == user_id,
        )

    def update_my_profile(self, *, user_id: UUID, body: UserProfileUpdateRequest) -> UserPublicProfileResponse:
        self._profiles.upsert(
            user_id,
            display_name=body.display_name,
            bio=body.bio,
            is_public=body.is_public,
        )
        self._session.commit()
        return self._profile_response(user_id, viewer_user_id=user_id)

    def get_profile(self, *, user_id: UUID, viewer_user_id: UUID) -> UserPublicProfileResponse:
        return self._profile_response(user_id, viewer_user_id=viewer_user_id)

    def list_directory(self, *, viewer_user_id: UUID, limit: int = 50) -> list[UserDirectoryEntry]:
        _ = viewer_user_id
        seen: set[UUID] = set()
        out: list[UserDirectoryEntry] = []
        for profile in self._profiles.list_discoverable(limit=limit):
            if profile.user_id in seen:
                continue
            count = self._published_count(profile.user_id)
            if count <= 0 and not profile.bio:
                continue
            seen.add(profile.user_id)
            out.append(
                UserDirectoryEntry(
                    user_id=profile.user_id,
                    display_name=self._display_name(profile.user_id),
                    bio=profile.bio,
                    published_voice_count=count,
                )
            )
        for entry in self._catalog.list_published():
            if entry.owner_user_id in seen:
                continue
            seen.add(entry.owner_user_id)
            profile = self._profiles.get(entry.owner_user_id)
            if profile and not profile.is_public:
                continue
            out.append(
                UserDirectoryEntry(
                    user_id=entry.owner_user_id,
                    display_name=self._display_name(entry.owner_user_id),
                    bio=profile.bio if profile else "",
                    published_voice_count=self._published_count(entry.owner_user_id),
                )
            )
            if len(out) >= limit:
                break
        return out[:limit]

    def send_message(self, *, sender_user_id: UUID, body: MessageCreateRequest) -> MessageResponse:
        if sender_user_id == body.recipient_user_id:
            raise SocialServiceError("INVALID_RECIPIENT", "不能给自己发消息", 400)
        recipient = self._users.get_by_id(body.recipient_user_id)
        if not recipient:
            raise SocialServiceError("USER_NOT_FOUND", "收件人不存在", 404)
        row = self._messages.create(
            sender_user_id=sender_user_id,
            recipient_user_id=body.recipient_user_id,
            body=body.body,
        )
        self._session.commit()
        return MessageResponse(
            message_id=row.id,
            sender_user_id=row.sender_user_id,
            recipient_user_id=row.recipient_user_id,
            body=row.body,
            read_at=row.read_at,
            created_at=row.created_at,
        )

    def list_conversations(self, *, user_id: UUID) -> list[ConversationPreviewResponse]:
        previews = self._messages.list_conversation_previews(user_id=user_id)
        return [
            ConversationPreviewResponse(
                peer_user_id=peer_id,
                peer_display_name=self._display_name(peer_id),
                last_message=body,
                last_at=last_at,
                unread_count=unread,
            )
            for peer_id, body, last_at, unread in previews
        ]

    def list_thread(self, *, user_id: UUID, peer_user_id: UUID) -> list[MessageResponse]:
        if not self._users.get_by_id(peer_user_id):
            raise SocialServiceError("USER_NOT_FOUND", "用户不存在", 404)
        self._messages.mark_thread_read(reader_user_id=user_id, peer_user_id=peer_user_id)
        self._session.commit()
        rows = self._messages.list_thread(user_a=user_id, user_b=peer_user_id)
        return [
            MessageResponse(
                message_id=r.id,
                sender_user_id=r.sender_user_id,
                recipient_user_id=r.recipient_user_id,
                body=r.body,
                read_at=r.read_at,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def _resolve_audio_path(self, demo_url: str) -> Path:
        marker = "/files/"
        if marker not in demo_url:
            raise SocialServiceError("DEMO_UNAVAILABLE", "样音文件不可用", 404)
        rel = demo_url.split(marker, 1)[1]
        storage = LocalStorage()
        path = Path(storage.absolute_path(rel))
        if not path.is_file():
            raise SocialServiceError("DEMO_UNAVAILABLE", "样音文件不存在", 404)
        return path

    def get_demo_download_path(self, *, catalog_id: UUID, user_id: UUID) -> tuple[Path, str]:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise SocialServiceError("CATALOG_NOT_FOUND", "音色未上架或不存在", 404)
        if not entry.demo_audio_url:
            raise SocialServiceError("DEMO_UNAVAILABLE", "该音色暂无样音，请稍后再试", 404)
        path = self._resolve_audio_path(entry.demo_audio_url)
        self._downloads.record(
            user_id=user_id,
            catalog_id=entry.id,
            voice_version_id=entry.voice_version_id,
            download_kind="demo",
        )
        self._session.commit()
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in entry.title[:40])
        return path, f"{safe or 'demo'}_sample.wav"

    def build_voice_pack(self, *, catalog_id: UUID, user_id: UUID) -> tuple[bytes, str]:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise SocialServiceError("CATALOG_NOT_FOUND", "音色未上架或不存在", 404)
        can_use = catalog_entry_can_use(self._session, entry, user_id)
        is_owner = entry.owner_user_id == user_id
        is_free = (entry.price_cents or 0) == 0
        if not (can_use or is_owner or is_free):
            raise SocialServiceError(
                "DOWNLOAD_FORBIDDEN",
                "需购买或获得授权后才能下载音色包",
                403,
            )
        if not entry.demo_audio_url:
            raise SocialServiceError("DEMO_UNAVAILABLE", "该音色暂无样音", 404)
        demo_path = self._resolve_audio_path(entry.demo_audio_url)
        meta = {
            "catalog_id": str(entry.id),
            "voice_version_id": str(entry.voice_version_id),
            "title": entry.title,
            "license_type": entry.license_type,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "notice": "本包仅含试听样音与授权说明；模型权重不在平台外分发。",
        }
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("license.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.writestr("README.txt", "Voice Studio 音色样音包\n请遵守 license.json 中的授权范围。\n")
            zf.write(demo_path, arcname="demo.wav")
        self._downloads.record(
            user_id=user_id,
            catalog_id=entry.id,
            voice_version_id=entry.voice_version_id,
            download_kind="voice_pack",
        )
        self._session.commit()
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in entry.title[:40])
        return buf.getvalue(), f"{safe or 'voice'}_pack.zip"
