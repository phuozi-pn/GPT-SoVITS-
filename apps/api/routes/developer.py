from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.developer.service import DeveloperService, DeveloperServiceError
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from voice_platform.developer.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeySummary,
    ApiKeyWebhookUpdateRequest,
)
from voice_platform.webhook.repository import WebhookDeliveryRepository

router = APIRouter()


class WebhookDeliverySummary(BaseModel):
    delivery_id: UUID
    channel: str
    target_url: str
    status: str
    attempts: int
    max_attempts: int
    last_status_code: int | None = None
    last_error: str | None = None
    delivered_at: str | None = None
    created_at: str | None = None


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


@router.patch("/developer/api-keys/{key_id}/webhook", response_model=ApiKeySummary)
def update_api_key_webhook(
    key_id: UUID,
    body: ApiKeyWebhookUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ApiKeySummary:
    try:
        return DeveloperService(session).update_webhook(user_id, key_id, body)
    except DeveloperServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/webhook-deliveries", response_model=list[WebhookDeliverySummary])
def list_webhook_deliveries(
    limit: int = 50,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[WebhookDeliverySummary]:
    rows = WebhookDeliveryRepository(session).list_recent(limit=min(limit, 200))
    return [
        WebhookDeliverySummary(
            delivery_id=r.id,
            channel=r.channel,
            target_url=r.target_url,
            status=r.status,
            attempts=r.attempts,
            max_attempts=r.max_attempts,
            last_status_code=r.last_status_code,
            last_error=r.last_error,
            delivered_at=r.delivered_at.isoformat() if r.delivered_at else None,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
