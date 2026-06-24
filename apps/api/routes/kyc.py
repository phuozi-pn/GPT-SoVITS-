from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.kyc.service import KycService, KycServiceError
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from voice_platform.kyc.schemas import (
    AdminKycUserSummary,
    AdminKycVerifyRequest,
    KycAuditEntry,
    KycStatusResponse,
    KycSubmitRequest,
    KycSubmitResponse,
)

router = APIRouter()


@router.get("/kyc/status", response_model=KycStatusResponse)
def kyc_status(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> KycStatusResponse:
    try:
        return KycService(session).get_status(user_id)
    except KycServiceError as exc:
        raise_domain_http(exc)


@router.post("/kyc/submit", response_model=KycSubmitResponse)
def kyc_submit(
    body: KycSubmitRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> KycSubmitResponse:
    try:
        return KycService(session).submit(
            user_id,
            real_name=body.real_name,
            id_number=body.id_number,
        )
    except KycServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/kyc/pending", response_model=list[AdminKycUserSummary])
def admin_kyc_pending(
    limit: int = 50,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[AdminKycUserSummary]:
    return KycService(session).list_pending_users(limit=min(limit, 200))


@router.get("/admin/kyc/{user_id}/audit", response_model=list[KycAuditEntry])
def admin_kyc_audit(
    user_id: UUID,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[KycAuditEntry]:
    return KycService(session).list_audit(user_id)


@router.post("/admin/kyc/{user_id}/verify", response_model=KycStatusResponse)
def admin_kyc_verify(
    user_id: UUID,
    body: AdminKycVerifyRequest | None = None,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> KycStatusResponse:
    try:
        return KycService(session).admin_verify(user_id, note=body.note if body else None)
    except KycServiceError as exc:
        raise_domain_http(exc)


@router.post("/admin/kyc/{user_id}/revoke", response_model=KycStatusResponse)
def admin_kyc_revoke(
    user_id: UUID,
    body: AdminKycVerifyRequest | None = None,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> KycStatusResponse:
    try:
        return KycService(session).admin_revoke(user_id, note=body.note if body else None)
    except KycServiceError as exc:
        raise_domain_http(exc)


@router.post("/kyc/webhooks/saas", response_model=KycStatusResponse)
async def kyc_saas_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> KycStatusResponse:
    body = await request.body()
    signature = request.headers.get("X-Kyc-Webhook-Signature")
    try:
        return KycService(session).process_saas_webhook(body=body, signature=signature)
    except KycServiceError as exc:
        raise_domain_http(exc)
