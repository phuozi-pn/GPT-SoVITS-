from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.developer.service import DeveloperService, DeveloperServiceError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.developer.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeySummary,
)

router = APIRouter()


@router.post("/developer/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    body: ApiKeyCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ApiKeyCreatedResponse:
    try:
        return DeveloperService(session).create_key(user_id, name=body.name)
    except DeveloperServiceError as exc:
        raise_domain_http(exc)


@router.get("/developer/api-keys", response_model=list[ApiKeySummary])
def list_api_keys(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[ApiKeySummary]:
    return DeveloperService(session).list_keys(user_id)


@router.delete("/developer/api-keys/{key_id}", response_model=ApiKeySummary)
def revoke_api_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ApiKeySummary:
    try:
        return DeveloperService(session).revoke_key(user_id, key_id)
    except DeveloperServiceError as exc:
        raise_domain_http(exc)
