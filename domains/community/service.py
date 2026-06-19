from __future__ import annotations

from datetime import datetime
from uuid import UUID

from voice_platform.auth.repository import UserRepository
from voice_platform.community.repository import (
    CommunityEventRepository,
    CommunityLikeRepository,
    CommunityPostRepository,
)
from voice_platform.community.schemas import (
    EventResponse,
    FeedItemResponse,
    FeedResponse,
    PostCreateRequest,
    PostResponse,
)
from voice_platform.social.repository import UserProfileRepository


class CommunityServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _split_tags(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()][:10]


class CommunityService:
    def __init__(self, session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._profiles = UserProfileRepository(session)
        self._posts = CommunityPostRepository(session)
        self._likes = CommunityLikeRepository(session)
        self._events = CommunityEventRepository(session)

    def _display_name(self, user_id: UUID) -> str:
        p = self._profiles.get(user_id)
        if p and p.display_name:
            return p.display_name
        u = self._users.get_by_id(user_id)
        if u and u.phone:
            digits = u.phone.strip()
            if len(digits) >= 7 and digits.isdigit():
                return f"{digits[:3]}****{digits[-4:]}"
            return digits
        return f"用户 · {str(user_id).split('-')[0]}"

    def create_post(self, *, author_user_id: UUID, body: PostCreateRequest) -> PostResponse:
        tags = [t.strip() for t in body.tags if t.strip()][:10]
        row = self._posts.create(author_user_id=author_user_id, body=body.body, tags=tags)
        self._session.commit()
        return PostResponse(
            post_id=row.id,
            author_user_id=row.author_user_id,
            author_display_name=self._display_name(row.author_user_id),
            body=row.body,
            tags=_split_tags(row.tags),
            created_at=row.created_at,
            like_count=0,
            liked_by_me=False,
        )

    def toggle_like(self, *, post_id: UUID, user_id: UUID) -> PostResponse:
        post = self._posts.get(post_id)
        if not post:
            raise CommunityServiceError("POST_NOT_FOUND", "帖子不存在", 404)
        liked = self._likes.like(post_id=post_id, user_id=user_id)
        if not liked:
            self._likes.unlike(post_id=post_id, user_id=user_id)
        self._session.commit()
        like_count = self._likes.count_for_posts([post_id]).get(post_id, 0)
        liked_by_me = post_id in self._likes.liked_by_me(post_ids=[post_id], user_id=user_id)
        return PostResponse(
            post_id=post.id,
            author_user_id=post.author_user_id,
            author_display_name=self._display_name(post.author_user_id),
            body=post.body,
            tags=_split_tags(post.tags),
            created_at=post.created_at,
            like_count=like_count,
            liked_by_me=liked_by_me,
        )

    def record_catalog_published(
        self,
        *,
        actor_user_id: UUID,
        catalog_id: UUID,
        title: str,
        price_cents: int,
    ) -> None:
        self._events.create(
            kind="catalog_published",
            actor_user_id=actor_user_id,
            target_type="catalog_voice",
            target_id=catalog_id,
            payload={"title": title, "price_cents": int(price_cents or 0)},
        )
        self._session.commit()

    def feed(self, *, viewer_user_id: UUID, before: datetime | None, limit: int = 30) -> FeedResponse:
        # Pull both streams then merge by created_at
        posts = self._posts.list_recent(before=before, limit=limit)
        events = self._events.list_recent(before=before, limit=limit)

        post_ids = [p.id for p in posts]
        like_counts = self._likes.count_for_posts(post_ids)
        liked_by_me = self._likes.liked_by_me(post_ids=post_ids, user_id=viewer_user_id)

        items: list[FeedItemResponse] = []
        for p in posts:
            items.append(
                FeedItemResponse(
                    type="post",
                    created_at=p.created_at,
                    post=PostResponse(
                        post_id=p.id,
                        author_user_id=p.author_user_id,
                        author_display_name=self._display_name(p.author_user_id),
                        body=p.body,
                        tags=_split_tags(p.tags),
                        created_at=p.created_at,
                        like_count=like_counts.get(p.id, 0),
                        liked_by_me=p.id in liked_by_me,
                    ),
                )
            )
        for e in events:
            items.append(
                FeedItemResponse(
                    type="event",
                    created_at=e.created_at,
                    event=EventResponse(
                        event_id=e.id,
                        kind=e.kind,
                        actor_user_id=e.actor_user_id,
                        actor_display_name=self._display_name(e.actor_user_id),
                        target_type=e.target_type,
                        target_id=e.target_id,
                        payload=e.payload or {},
                        created_at=e.created_at,
                    ),
                )
            )

        items.sort(key=lambda x: x.created_at, reverse=True)
        items = items[:limit]
        next_before = None
        if items:
            next_before = items[-1].created_at.isoformat()
        return FeedResponse(items=items, next_before=next_before)

