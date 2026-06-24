"""Payment checkout and webhook schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CheckoutResponse(BaseModel):
    order_id: UUID
    status: str
    amount_cents: int
    currency: str
    provider: str
    provider_ref: str
    checkout_url: str | None = None
    qr_code_url: str | None = None
    authorization_id: UUID | None = None


class PaymentOrderStatusResponse(BaseModel):
    order_id: UUID
    status: str
    amount_cents: int
    provider: str
    provider_ref: str
    authorization_id: UUID | None = None
    paid_at: datetime | None = None
    created_at: datetime | None = None


class PaymentWebhookPayload(BaseModel):
    order_id: UUID
    provider_ref: str
    status: str = "paid"


class MockPaymentConfirmResponse(BaseModel):
    order_id: UUID
    status: str
    authorization_id: UUID
