"""Payment provider registry."""

from __future__ import annotations

from voice_platform.payment.providers.alipay import AlipayPaymentProvider
from voice_platform.payment.providers.base import (
    CheckoutOrderContext,
    CheckoutSession,
    PaymentProvider,
    PaymentProviderError,
)
from voice_platform.payment.providers.mock import MockPaymentProvider
from voice_platform.payment.providers.wechat import WechatPaymentProvider

_PROVIDERS: dict[str, type[PaymentProvider]] = {
    "mock": MockPaymentProvider,
    "wechat": WechatPaymentProvider,
    "alipay": AlipayPaymentProvider,
}


def get_payment_provider(name: str) -> PaymentProvider:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise PaymentProviderError("UNKNOWN_PROVIDER", f"Unknown payment provider: {name}")
    return cls()
