from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TokenPackageResponse(BaseModel):
    sku: str
    label: str
    token_amount: int
    price_cents: int
    hint: str
    mock_payment: bool = True


class UserWalletResponse(BaseModel):
    user_id: UUID
    token_balance: int
    total_purchased_tokens: int


class WalletLedgerEntry(BaseModel):
    entry_id: UUID
    kind: str
    token_delta: int
    balance_after: int
    job_id: UUID | None = None
    package_sku: str | None = None
    note: str | None = None
    created_at: datetime


class WalletPurchaseRequest(BaseModel):
    package_sku: str = Field(min_length=1, max_length=64)


class WalletPurchaseResponse(BaseModel):
    package_sku: str
    tokens_granted: int
    token_balance: int
    mock_payment: bool = True
