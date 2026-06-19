from __future__ import annotations

from datetime import datetime
from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_viewer_user_id
from apps.api.exceptions import raise_domain_http
from domains.community.service import CommunityService, CommunityServiceError
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from voice_platform.community.schemas import FeedResponse, PostCreateRequest, PostResponse

router = APIRouter()


@router.get("/community/feed", response_model=FeedResponse)
def get_feed(
    before: str | None = Query(default=None, description="ISO datetime cursor"),
    limit: int = Query(default=30, ge=1, le=60),
    user_id: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
) -> FeedResponse:
    dt = None
    if before:
        try:
            dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
        except ValueError:
            dt = None
    return CommunityService(session).feed(viewer_user_id=user_id, before=dt, limit=limit)


@router.post("/community/posts", response_model=PostResponse, status_code=201)
def create_post(
    body: PostCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PostResponse:
    try:
        return CommunityService(session).create_post(author_user_id=user_id, body=body)
    except CommunityServiceError as exc:
        raise_domain_http(exc)


@router.post("/community/posts/{post_id}/like", response_model=PostResponse)
def toggle_like(
    post_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PostResponse:
    try:
        return CommunityService(session).toggle_like(post_id=post_id, user_id=user_id)
    except CommunityServiceError as exc:
        raise_domain_http(exc)

