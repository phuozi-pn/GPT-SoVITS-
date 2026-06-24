from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_viewer_user_id, require_admin_user
from apps.api.exceptions import parse_tag_query, raise_domain_http
from domains.marketplace.service import MarketplaceService, MarketplaceServiceError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.job.schemas import (
    CatalogEntryResponse,
    CatalogPublishRequest,
    CatalogRejectRequest,
    CreatorProfileResponse,
    VoiceGrantCreateRequest,
    VoiceGrantResponse,
)

router = APIRouter()


@router.get("/catalog/tags", response_model=list[str])
def list_catalog_tags(
    _: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
) -> list[str]:
    return MarketplaceService(session).list_catalog_tags()


@router.get("/catalog/voices", response_model=list[CatalogEntryResponse])
def list_catalog_voices(
    featured: bool = False,
    tag: str | None = None,
    tags: str | None = None,
    owner: UUID | None = None,
    user_id: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
) -> list[CatalogEntryResponse]:
    tag_filter = parse_tag_query(tag=tag, tags=tags)
    return MarketplaceService(session).list_catalog(
        user_id=user_id,
        featured_only=featured,
        tags=tag_filter or None,
        owner_user_id=owner,
    )


@router.get("/catalog/creators/{owner_user_id}", response_model=CreatorProfileResponse)
def get_creator_profile(
    owner_user_id: UUID,
    featured: bool = False,
    tag: str | None = None,
    tags: str | None = None,
    user_id: UUID = Depends(get_viewer_user_id),
    session: Session = Depends(get_session),
) -> CreatorProfileResponse:
    tag_filter = parse_tag_query(tag=tag, tags=tags)
    return MarketplaceService(session).get_creator_profile(
        owner_user_id=owner_user_id,
        viewer_user_id=user_id,
        featured_only=featured,
        tags=tag_filter or None,
    )


@router.get("/catalog/voices/mine", response_model=list[CatalogEntryResponse])
def list_my_catalog_submissions(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[CatalogEntryResponse]:
    return MarketplaceService(session).list_my_submissions(owner_user_id=user_id)


@router.get("/catalog/voices/pending", response_model=list[CatalogEntryResponse])
def list_pending_catalog_voices(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[CatalogEntryResponse]:
    return MarketplaceService(session).list_pending_review()


@router.post("/catalog/voices", response_model=CatalogEntryResponse, status_code=201)
def publish_catalog_voice(
    body: CatalogPublishRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).publish_to_catalog(owner_user_id=user_id, body=body)
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.post("/catalog/voices/{catalog_id}/approve", response_model=CatalogEntryResponse)
def approve_catalog_voice(
    catalog_id: UUID,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).approve_catalog_entry(catalog_id=catalog_id)
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.post("/catalog/voices/{catalog_id}/generate-demo", response_model=CatalogEntryResponse)
def regenerate_catalog_demo(
    catalog_id: UUID,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).regenerate_catalog_demo(catalog_id=catalog_id)
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.post("/catalog/voices/{catalog_id}/reject", response_model=CatalogEntryResponse)
def reject_catalog_voice(
    catalog_id: UUID,
    body: CatalogRejectRequest,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).reject_catalog_entry(
            catalog_id=catalog_id,
            reason=body.reason,
        )
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.post("/catalog/voices/{catalog_id}/unpublish", response_model=CatalogEntryResponse)
def unpublish_catalog_voice(
    catalog_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).unpublish_catalog_entry(
            catalog_id=catalog_id,
            owner_user_id=user_id,
        )
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.get("/voice-grants/issued", response_model=list[VoiceGrantResponse])
def list_issued_grants(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[VoiceGrantResponse]:
    return MarketplaceService(session).list_grants_issued(granter_user_id=user_id)


@router.get("/voice-grants", response_model=list[VoiceGrantResponse])
def list_my_grants(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[VoiceGrantResponse]:
    return MarketplaceService(session).list_grants_received(grantee_user_id=user_id)


@router.post("/voices/{voice_id}/grants", response_model=VoiceGrantResponse, status_code=201)
def create_voice_grant(
    voice_id: UUID,
    body: VoiceGrantCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceGrantResponse:
    try:
        return MarketplaceService(session).create_grant(
            voice_id=voice_id,
            granter_user_id=user_id,
            body=body,
        )
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)


@router.delete("/voice-grants/{grant_id}", status_code=204)
def revoke_voice_grant(
    grant_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> None:
    try:
        MarketplaceService(session).revoke_grant(grant_id=grant_id, granter_user_id=user_id)
    except MarketplaceServiceError as exc:
        raise_domain_http(exc)
