from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from voice_platform.auth.models import UserRow
from voice_platform.social.models import UserMessageRow, UserProfileRow, VoiceDownloadEventRow


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> UserProfileRow | None:
        return self._session.get(UserProfileRow, user_id)

    def upsert(
        self,
        user_id: UUID,
        *,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
        is_public: bool | None = None,
    ) -> UserProfileRow:
        row = self.get(user_id)
        if not row:
            row = UserProfileRow(user_id=user_id)
            self._session.add(row)
        if display_name is not None:
            row.display_name = display_name.strip() or None
        if bio is not None:
            row.bio = bio.strip()
        if avatar_url is not None:
            row.avatar_url = avatar_url.strip() or None
        if is_public is not None:
            row.is_public = is_public
        self._session.flush()
        return row

    def list_discoverable(self, *, limit: int = 50) -> list[UserProfileRow]:
        stmt = (
            select(UserProfileRow)
            .where(UserProfileRow.is_public.is_(True))
            .order_by(UserProfileRow.updated_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))


class UserMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        sender_user_id: UUID,
        recipient_user_id: UUID,
        body: str,
        conversation_peer_user_id: UUID | None = None,
    ) -> UserMessageRow:
        row = UserMessageRow(
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            conversation_peer_user_id=conversation_peer_user_id,
            body=body.strip(),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_thread(self, *, user_a: UUID, user_b: UUID, limit: int = 100) -> list[UserMessageRow]:
        stmt = (
            select(UserMessageRow)
            .where(
                or_(
                    (UserMessageRow.sender_user_id == user_a) & (UserMessageRow.recipient_user_id == user_b),
                    (UserMessageRow.sender_user_id == user_b) & (UserMessageRow.recipient_user_id == user_a),
                    (UserMessageRow.recipient_user_id == user_a)
                    & (UserMessageRow.conversation_peer_user_id == user_b),
                    (UserMessageRow.recipient_user_id == user_b)
                    & (UserMessageRow.conversation_peer_user_id == user_a),
                )
            )
            .order_by(UserMessageRow.created_at.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def list_conversation_previews(self, *, user_id: UUID, limit: int = 30) -> list[tuple[UUID, str, datetime, int]]:
        """Return (peer_id, last_body, last_at, unread_count)."""
        stmt = (
            select(UserMessageRow)
            .where(
                or_(
                    UserMessageRow.sender_user_id == user_id,
                    UserMessageRow.recipient_user_id == user_id,
                )
            )
            .order_by(UserMessageRow.created_at.desc())
            .limit(200)
        )
        rows = list(self._session.scalars(stmt))

        # Aggregate in Python for correctness and portability.
        last_by_peer: dict[UUID, UserMessageRow] = {}
        unread_by_peer: dict[UUID, int] = {}
        for m in rows:
            if m.conversation_peer_user_id is not None and m.recipient_user_id == user_id:
                peer = m.conversation_peer_user_id
            else:
                peer = m.recipient_user_id if m.sender_user_id == user_id else m.sender_user_id
            if peer not in last_by_peer:
                last_by_peer[peer] = m
            if m.recipient_user_id == user_id and m.read_at is None:
                unread_by_peer[peer] = unread_by_peer.get(peer, 0) + 1

        out: list[tuple[UUID, str, datetime, int]] = []
        for peer, last in last_by_peer.items():
            out.append((peer, last.body, last.created_at, unread_by_peer.get(peer, 0)))
        out.sort(key=lambda x: x[2], reverse=True)
        return out[:limit]

    def mark_thread_read(self, *, reader_user_id: UUID, peer_user_id: UUID) -> int:
        stmt = (
            update(UserMessageRow)
            .where(
                UserMessageRow.recipient_user_id == reader_user_id,
                or_(
                    UserMessageRow.sender_user_id == peer_user_id,
                    UserMessageRow.conversation_peer_user_id == peer_user_id,
                ),
                UserMessageRow.read_at.is_(None),
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        result = self._session.execute(stmt)
        return int(result.rowcount or 0)


class VoiceDownloadEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        user_id: UUID,
        catalog_id: UUID,
        voice_version_id: UUID,
        download_kind: str,
    ) -> None:
        self._session.add(
            VoiceDownloadEventRow(
                user_id=user_id,
                catalog_id=catalog_id,
                voice_version_id=voice_version_id,
                download_kind=download_kind,
            )
        )
        self._session.flush()


class UserDirectoryRepository:
    """Helpers to list users with published catalog voices."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_user(self, user_id: UUID) -> UserRow | None:
        return self._session.get(UserRow, user_id)
