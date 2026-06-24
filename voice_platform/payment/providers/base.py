"""Payment provider interface (Phase 4 — REQ-017)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


class PaymentProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CheckoutSession:
    checkout_url: str | None = None
    qr_code_url: str | None = None


@dataclass(frozen=True)
class CheckoutOrderContext:
    order_id: UUID
    amount_cents: int
    currency: str
    provider_ref: str
    buyer_user_id: UUID
    catalog_id: UUID
    catalog_title: str


class PaymentProvider:
    name: str = "base"

    def create_checkout(self, order: CheckoutOrderContext) -> CheckoutSession:
        raise NotImplementedError

    def supports_mock_confirm(self) -> bool:
        return False
