from __future__ import annotations

from uuid import UUID

from apps.api.config import get_settings
from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.payment.service import PaymentService, PaymentServiceError
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from voice_platform.payment.schemas import (
    CheckoutResponse,
    MockPaymentConfirmResponse,
    PaymentOrderStatusResponse,
)

router = APIRouter()


@router.post(
    "/catalog/voices/{catalog_id}/checkout",
    response_model=CheckoutResponse,
    status_code=201,
)
def checkout_catalog_voice(
    catalog_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CheckoutResponse:
    try:
        return PaymentService(session).checkout(catalog_id=catalog_id, buyer_user_id=user_id)
    except PaymentServiceError as exc:
        raise_domain_http(exc)


@router.get("/payments/orders/{order_id}", response_model=PaymentOrderStatusResponse)
def get_payment_order(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PaymentOrderStatusResponse:
    try:
        return PaymentService(session).get_order(order_id=order_id, buyer_user_id=user_id)
    except PaymentServiceError as exc:
        raise_domain_http(exc)


@router.post(
    "/payments/orders/{order_id}/mock-confirm",
    response_model=MockPaymentConfirmResponse,
)
def mock_confirm_payment(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> MockPaymentConfirmResponse:
    if get_settings().payment_provider != "mock":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return PaymentService(session).mock_confirm(order_id=order_id, buyer_user_id=user_id)
    except PaymentServiceError as exc:
        raise_domain_http(exc)


@router.post("/payments/webhooks/{provider}", response_model=PaymentOrderStatusResponse)
async def payment_webhook(
    provider: str,
    request: Request,
    session: Session = Depends(get_session),
) -> PaymentOrderStatusResponse:
    body = await request.body()
    signature = request.headers.get("X-Payment-Signature")
    try:
        return PaymentService(session).process_webhook(
            provider=provider,
            body=body,
            signature=signature,
        )
    except PaymentServiceError as exc:
        raise_domain_http(exc)
