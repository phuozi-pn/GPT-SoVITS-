"""为音色馆条目与创作者补齐默认头像/封面。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.marketplace.avatar_defaults import default_catalog_cover_url, default_creator_avatar_url
from domains.marketplace.cover_image import to_public_files_url
from voice_platform.config import get_settings
from voice_platform.job.models import VoiceCatalogEntryRow
from voice_platform.job.repository import VoiceCatalogRepository
from voice_platform.social.repository import UserProfileRepository


@dataclass
class AvatarBackfillResult:
    covers_assigned: int = 0
    covers_relinked: int = 0
    avatars_assigned: int = 0
    owners_touched: int = 0


class AvatarAssignService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._catalog = VoiceCatalogRepository(session)
        self._profiles = UserProfileRepository(session)

    def ensure_catalog_cover(self, entry: VoiceCatalogEntryRow) -> bool:
        if (entry.cover_image_url or "").strip():
            return False
        tags = list(entry.tags_json or [])
        url = default_catalog_cover_url(tags)
        self._catalog.set_cover_image_url(entry.id, cover_image_url=url)
        entry.cover_image_url = url
        return True

    def ensure_creator_avatar(self, owner_user_id: UUID) -> bool:
        profile = self._profiles.get(owner_user_id)
        if profile and (profile.avatar_url or "").strip():
            return False
        url = default_creator_avatar_url(user_id=owner_user_id)
        self._profiles.upsert(owner_user_id, avatar_url=url)
        self._session.commit()
        return True

    def relink_stored_covers(self) -> int:
        """若磁盘上已有 catalog/covers/{catalog_id}.*，把 DB 封面 URL 指回 /files/...。"""
        root = Path(get_settings().storage_root)
        relinked = 0
        rows = list(self._session.scalars(select(VoiceCatalogEntryRow)).all())
        for entry in rows:
            for ext in ("png", "jpg", "jpeg", "webp"):
                rel = f"{entry.owner_user_id}/catalog/covers/{entry.id}.{ext}"
                if not (root / rel).is_file():
                    continue
                url = to_public_files_url(rel)
                if (entry.cover_image_url or "").strip() != url:
                    self._catalog.set_cover_image_url(entry.id, cover_image_url=url)
                    entry.cover_image_url = url
                    relinked += 1
                break
        return relinked

    def backfill_all(self) -> AvatarBackfillResult:
        result = AvatarBackfillResult()
        owners: set[UUID] = set()

        result.covers_relinked = self.relink_stored_covers()

        rows = list(
            self._session.scalars(
                select(VoiceCatalogEntryRow).where(
                    VoiceCatalogEntryRow.status.in_(("published", "pending"))
                )
            ).all()
        )
        for entry in rows:
            if self.ensure_catalog_cover(entry):
                result.covers_assigned += 1
            owners.add(entry.owner_user_id)

        for owner_id in owners:
            if self.ensure_creator_avatar(owner_id):
                result.avatars_assigned += 1
                result.owners_touched += 1

        return result
