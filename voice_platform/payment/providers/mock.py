"""Mock payment provider — local dev and smoke tests."""

from __future__ import annotations

from voice_platform.payment.providers.base import (
    CheckoutOrderContext,
    CheckoutSession,
    PaymentProvider,
)


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_checkout(self, order: CheckoutOrderContext) -> CheckoutSession:
        return CheckoutSession(
            checkout_url=f"/api/v1/payments/orders/{order.order_id}/mock-confirm",
        )

    def supports_mock_confirm(self) -> bool:
        return True
