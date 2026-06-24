from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.consents.service import ConsentService, ConsentServiceError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from voice_platform.job.schemas import ConsentCreateRequest, ConsentCreateResponse, ConsentAdminSummary, ConsentRejectRequest

router = APIRouter()


@router.post("/consents", response_model=ConsentCreateResponse, status_code=201)
def create_consent(
    body: ConsentCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ConsentCreateResponse:
    service = ConsentService(session)
    try:
        return service.create(owner_user_id=user_id, voice_id=body.voice_id)
    except ConsentServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/consents/pending", response_model=list[ConsentAdminSummary])
def list_pending_consents(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[ConsentAdminSummary]:
    return ConsentService(session).list_pending()


@router.post("/admin/consents/{consent_id}/approve", response_model=ConsentAdminSummary)
def approve_consent(
    consent_id: UUID,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> ConsentAdminSummary:
    try:
        return ConsentService(session).approve(consent_id=consent_id, admin_user_id=admin_id)
    except ConsentServiceError as exc:
        raise_domain_http(exc)


@router.post("/admin/consents/{consent_id}/reject", response_model=ConsentAdminSummary)
def reject_consent(
    consent_id: UUID,
    body: ConsentRejectRequest,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> ConsentAdminSummary:
    try:
        return ConsentService(session).reject(
            consent_id=consent_id,
            admin_user_id=admin_id,
            reason=body.reason,
        )
    except ConsentServiceError as exc:
        raise_domain_http(exc)
