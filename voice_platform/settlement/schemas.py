from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SellerWalletResponse(BaseModel):
    seller_user_id: UUID
    balance_cents: int
    pending_payout_cents: int
    total_earned_cents: int
    platform_fee_bps: int
    min_payout_cents: int


class SellerLedgerEntry(BaseModel):
    entry_id: UUID
    kind: str
    gross_cents: int
    fee_cents: int
    net_cents: int
    balance_after_cents: int
    payment_order_id: UUID | None = None
    note: str | None = None
    created_at: datetime | None = None


class PayoutRequestBody(BaseModel):
    amount_cents: int = Field(gt=0)


class PayoutRequestResponse(BaseModel):
    payout_id: UUID
    seller_user_id: UUID
    amount_cents: int
    status: str
    note: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None


class AdminPayoutActionBody(BaseModel):
    note: str | None = Field(default=None, max_length=200)
