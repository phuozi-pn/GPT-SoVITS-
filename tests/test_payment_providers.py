"""Payment provider registry tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from voice_platform.payment.providers import get_payment_provider
from voice_platform.payment.providers.base import CheckoutOrderContext, PaymentProviderError
from voice_platform.payment.providers.mock import MockPaymentProvider


def test_get_mock_provider():
    provider = get_payment_provider("mock")
    assert isinstance(provider, MockPaymentProvider)
    assert provider.supports_mock_confirm() is True


def test_mock_checkout_url():
    provider = get_payment_provider("mock")
    order_id = UUID("55555555-5555-5555-5555-555555555555")
    session = provider.create_checkout(
        CheckoutOrderContext(
            order_id=order_id,
            amount_cents=9900,
            currency="CNY",
            provider_ref="chk_test",
            buyer_user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            catalog_id=UUID("22222222-2222-2222-2222-222222222222"),
            catalog_title="Test Voice",
        )
    )
    assert session.checkout_url == f"/api/v1/payments/orders/{order_id}/mock-confirm"


def test_wechat_not_configured():
    with pytest.raises(PaymentProviderError) as exc:
        get_payment_provider("wechat").create_checkout(
            CheckoutOrderContext(
                order_id=UUID("55555555-5555-5555-5555-555555555555"),
                amount_cents=100,
                currency="CNY",
                provider_ref="chk_x",
                buyer_user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                catalog_id=UUID("22222222-2222-2222-2222-222222222222"),
                catalog_title="x",
            )
        )
    assert exc.value.code == "WECHAT_NOT_CONFIGURED"


def test_alipay_not_configured():
    with pytest.raises(PaymentProviderError) as exc:
        get_payment_provider("alipay").create_checkout(
            CheckoutOrderContext(
                order_id=UUID("55555555-5555-5555-5555-555555555555"),
                amount_cents=100,
                currency="CNY",
                provider_ref="chk_x",
                buyer_user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                catalog_id=UUID("22222222-2222-2222-2222-222222222222"),
                catalog_title="x",
            )
        )
    assert exc.value.code == "ALIPAY_NOT_CONFIGURED"
