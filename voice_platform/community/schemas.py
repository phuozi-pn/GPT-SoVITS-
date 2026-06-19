from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class PostResponse(BaseModel):
    post_id: UUID
    author_user_id: UUID
    author_display_name: str
    body: str
    tags: list[str]
    created_at: datetime
    like_count: int
    liked_by_me: bool


class EventResponse(BaseModel):
    event_id: UUID
    kind: str
    actor_user_id: UUID
    actor_display_name: str
    target_type: str
    target_id: UUID
    payload: dict
    created_at: datetime


class FeedItemResponse(BaseModel):
    type: Literal["post", "event"]
    created_at: datetime
    post: PostResponse | None = None
    event: EventResponse | None = None


class FeedResponse(BaseModel):
    items: list[FeedItemResponse]
    next_before: str | None = None

