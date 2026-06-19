from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.orm import Session

from voice_platform.community.models import CommunityEventRow, CommunityPostLikeRow, CommunityPostRow


class CommunityPostRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, author_user_id: UUID, body: str, tags: list[str]) -> CommunityPostRow:
        row = CommunityPostRow(
            author_user_id=author_user_id,
            body=body.strip(),
            tags=",".join([t.strip() for t in tags if t.strip()][:10]),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get(self, post_id: UUID) -> CommunityPostRow | None:
        return self._session.get(CommunityPostRow, post_id)

    def list_recent(self, *, before: datetime | None, limit: int) -> list[CommunityPostRow]:
        stmt = select(CommunityPostRow).order_by(desc(CommunityPostRow.created_at)).limit(limit)
        if before is not None:
            stmt = stmt.where(CommunityPostRow.created_at < before)
        return list(self._session.scalars(stmt))


class CommunityLikeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def like(self, *, post_id: UUID, user_id: UUID) -> bool:
        exists = self._session.get(CommunityPostLikeRow, {"post_id": post_id, "user_id": user_id})
        if exists:
            return False
        row = CommunityPostLikeRow(post_id=post_id, user_id=user_id)
        self._session.add(row)
        self._session.flush()
        return True

    def unlike(self, *, post_id: UUID, user_id: UUID) -> bool:
        stmt = delete(CommunityPostLikeRow).where(
            and_(
                CommunityPostLikeRow.post_id == post_id,
                CommunityPostLikeRow.user_id == user_id,
            )
        )
        result = self._session.execute(stmt)
        return bool(result.rowcount or 0)

    def count_for_posts(self, post_ids: list[UUID]) -> dict[UUID, int]:
        if not post_ids:
            return {}
        stmt = (
            select(CommunityPostLikeRow.post_id, func.count().label("c"))
            .where(CommunityPostLikeRow.post_id.in_(post_ids))
            .group_by(CommunityPostLikeRow.post_id)
        )
        out: dict[UUID, int] = {}
        for pid, c in self._session.execute(stmt):
            out[pid] = int(c)
        return out

    def liked_by_me(self, *, post_ids: list[UUID], user_id: UUID) -> set[UUID]:
        if not post_ids:
            return set()
        stmt = select(CommunityPostLikeRow.post_id).where(
            and_(
                CommunityPostLikeRow.user_id == user_id,
                CommunityPostLikeRow.post_id.in_(post_ids),
            )
        )
        return set(self._session.execute(stmt).scalars().all())


class CommunityEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        kind: str,
        actor_user_id: UUID,
        target_type: str,
        target_id: UUID,
        payload: dict,
    ) -> CommunityEventRow:
        row = CommunityEventRow(
            kind=kind,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_recent(self, *, before: datetime | None, limit: int) -> list[CommunityEventRow]:
        stmt = select(CommunityEventRow).order_by(desc(CommunityEventRow.created_at)).limit(limit)
        if before is not None:
            stmt = stmt.where(CommunityEventRow.created_at < before)
        return list(self._session.scalars(stmt))

