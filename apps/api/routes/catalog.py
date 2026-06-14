from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.marketplace.service import MarketplaceService, MarketplaceServiceError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session
from voice_platform.job.schemas import (
    CatalogEntryResponse,
    CatalogPublishRequest,
    VoiceGrantCreateRequest,
    VoiceGrantResponse,
)

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/catalog/voices", response_model=list[CatalogEntryResponse])
def list_catalog_voices(
    featured: bool = False,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[CatalogEntryResponse]:
    return MarketplaceService(session).list_catalog(user_id=user_id, featured_only=featured)


@router.post("/catalog/voices", response_model=CatalogEntryResponse, status_code=201)
def publish_catalog_voice(
    body: CatalogPublishRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return MarketplaceService(session).publish_to_catalog(owner_user_id=user_id, body=body)
    except MarketplaceServiceError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


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
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.delete("/voice-grants/{grant_id}", status_code=204)
def revoke_voice_grant(
    grant_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> None:
    try:
        MarketplaceService(session).revoke_grant(grant_id=grant_id, granter_user_id=user_id)
    except MarketplaceServiceError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
