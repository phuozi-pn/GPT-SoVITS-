from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.licensing.service import LicensingService, LicensingServiceError
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from voice_platform.job.schemas import (
    AuthorizationCertificateResponse,
    AuthorizationResponse,
    AuthorizationVerifyResponse,
    CatalogEntryResponse,
    CatalogLicensePolicyRequest,
    ComplaintCreateRequest,
    ComplaintResponse,
    PaymentOrderResponse,
)

router = APIRouter()


@router.patch("/catalog/voices/{catalog_id}/license", response_model=CatalogEntryResponse)
def update_catalog_license(
    catalog_id: UUID,
    body: CatalogLicensePolicyRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CatalogEntryResponse:
    try:
        return LicensingService(session).update_license_policy(
            catalog_id=catalog_id,
            owner_user_id=user_id,
            body=body,
        )
    except LicensingServiceError as exc:
        raise_domain_http(exc)


@router.post(
    "/catalog/voices/{catalog_id}/purchase",
    response_model=AuthorizationResponse,
    status_code=201,
)
def purchase_catalog_voice(
    catalog_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AuthorizationResponse:
    try:
        return LicensingService(session).purchase(catalog_id=catalog_id, buyer_user_id=user_id)
    except LicensingServiceError as exc:
        raise_domain_http(exc)


@router.get("/authorizations", response_model=list[AuthorizationResponse])
def list_my_authorizations(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[AuthorizationResponse]:
    return LicensingService(session).list_purchases(buyer_user_id=user_id)


@router.get("/authorizations/issued", response_model=list[AuthorizationResponse])
def list_issued_authorizations(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[AuthorizationResponse]:
    return LicensingService(session).list_sales(seller_user_id=user_id)


@router.get(
    "/authorizations/{authorization_id}/certificate",
    response_model=AuthorizationCertificateResponse,
)
def export_authorization_certificate(
    authorization_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AuthorizationCertificateResponse:
    try:
        return LicensingService(session).get_certificate(
            authorization_id=authorization_id,
            user_id=user_id,
        )
    except LicensingServiceError as exc:
        raise_domain_http(exc)


@router.get("/authorizations/{authorization_id}/certificate.pdf")
def export_authorization_certificate_pdf(
    authorization_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> Response:
    try:
        pdf_bytes = LicensingService(session).build_certificate_pdf(
            authorization_id=authorization_id,
            user_id=user_id,
        )
    except LicensingServiceError as exc:
        raise_domain_http(exc)
    filename = f"authorization-{authorization_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/authorizations/{authorization_id}/verify",
    response_model=AuthorizationVerifyResponse,
)
def verify_authorization(
    authorization_id: UUID,
    session: Session = Depends(get_session),
) -> AuthorizationVerifyResponse:
    return LicensingService(session).verify_certificate(authorization_id)


@router.post("/complaints", response_model=ComplaintResponse, status_code=201)
def submit_complaint(
    body: ComplaintCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ComplaintResponse:
    try:
        return LicensingService(session).submit_complaint(reporter_user_id=user_id, body=body)
    except LicensingServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/payments", response_model=list[PaymentOrderResponse])
def list_admin_payments(
    limit: int = 50,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[PaymentOrderResponse]:
    return LicensingService(session).list_payment_orders(limit=min(limit, 200))


@router.get("/admin/complaints", response_model=list[ComplaintResponse])
def list_admin_complaints(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[ComplaintResponse]:
    return LicensingService(session).list_open_complaints()


@router.post("/admin/complaints/{complaint_id}/takedown", response_model=ComplaintResponse)
def admin_takedown_complaint(
    complaint_id: UUID,
    resolution_note: str = "",
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> ComplaintResponse:
    try:
        return LicensingService(session).takedown_complaint(
            complaint_id=complaint_id,
            admin_user_id=admin_id,
            resolution_note=resolution_note,
        )
    except LicensingServiceError as exc:
        raise_domain_http(exc)


@router.post("/admin/complaints/{complaint_id}/dismiss", response_model=ComplaintResponse)
def admin_dismiss_complaint(
    complaint_id: UUID,
    resolution_note: str = "",
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> ComplaintResponse:
    try:
        return LicensingService(session).dismiss_complaint(
            complaint_id=complaint_id,
            admin_user_id=admin_id,
            resolution_note=resolution_note,
        )
    except LicensingServiceError as exc:
        raise_domain_http(exc)
