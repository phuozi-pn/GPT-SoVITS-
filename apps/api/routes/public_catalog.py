"""Public catalog API — REQ-029: no-login-required open marketplace."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_session, get_viewer_user_id
from apps.api.exceptions import parse_tag_query
from domains.marketplace.service import MarketplaceService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from voice_platform.job.schemas import CatalogEntryResponse

router = APIRouter()


@router.get("/public/catalog", response_model=list[CatalogEntryResponse])
def list_public_catalog(
    featured: bool = Query(default=False, description="Show featured/popular voices only"),
    tag: str | None = Query(default=None, description="Filter by tag"),
    tags: str | None = Query(default=None, description="Filter by comma-separated tags"),
    owner: UUID | None = Query(default=None, description="Filter by creator"),
    page: int = Query(default=1, ge=1, le=100, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    user_id: UUID = Depends(get_viewer_user_id),  # supports anonymous via dev mode
    session: Session = Depends(get_session),
) -> list[CatalogEntryResponse]:
    """List published catalog entries — no login required."""
    tag_list = parse_tag_query(tag=tag, tags=tags)

    service = MarketplaceService(session)
    entries = service.list_catalog(
        user_id=user_id,
        featured_only=featured,
        tags=tag_list if tag_list else None,
        owner_user_id=owner,
    )

    # Simple pagination
    start = (page - 1) * page_size
    return entries[start : start + page_size]


@router.get("/public/catalog/tags", response_model=list[str])
def list_public_catalog_tags(
    _: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
) -> list[str]:
    """List all catalog tags — no login required."""
    return MarketplaceService(session).list_catalog_tags()


@router.get("/public/catalog/stats")
def public_catalog_stats(
    _: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
):
    """Get public catalog statistics."""
    all_entries = MarketplaceService(session).list_catalog(user_id=None, featured_only=False, tags=None)
    featured = MarketplaceService(session).list_catalog(user_id=None, featured_only=True, tags=None)
    tags = MarketplaceService(session).list_catalog_tags()
    return {
        "total_voices": len(all_entries),
        "featured_voices": len(featured),
        "tags_count": len(tags),
    }
