"""Alipay face-to-face precreate (QR code)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx

from voice_platform.config import get_settings
from voice_platform.payment.providers._rsa import load_private_key_pem, sign_sha256_rsa
from voice_platform.payment.providers.base import (
    CheckoutOrderContext,
    CheckoutSession,
    PaymentProvider,
    PaymentProviderError,
)


class AlipayPaymentProvider(PaymentProvider):
    name = "alipay"

    def _settings(self):
        return get_settings()

    def _ensure_config(self) -> None:
        s = self._settings()
        if not s.alipay_app_id:
            raise PaymentProviderError("ALIPAY_NOT_CONFIGURED", "Set ALIPAY_APP_ID")
        if not (s.alipay_private_key or s.alipay_private_key_path):
            raise PaymentProviderError(
                "ALIPAY_NOT_CONFIGURED",
                "Set ALIPAY_PRIVATE_KEY or ALIPAY_PRIVATE_KEY_PATH",
            )
        if not s.payment_notify_base_url:
            raise PaymentProviderError(
                "ALIPAY_NOT_CONFIGURED",
                "Set PAYMENT_NOTIFY_BASE_URL for Alipay notify_url",
            )

    def create_checkout(self, order: CheckoutOrderContext) -> CheckoutSession:
        self._ensure_config()
        settings = self._settings()
        biz_content = {
            "out_trade_no": order.provider_ref,
            "total_amount": f"{order.amount_cents / 100:.2f}",
            "subject": order.catalog_title[:256] or "Voice catalog purchase",
        }
        params = {
            "app_id": settings.alipay_app_id,
            "method": "alipay.trade.precreate",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": f"{settings.payment_notify_base_url.rstrip('/')}/api/v1/payments/webhooks/alipay",
            "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }
        sign = self._sign_params(params)
        params["sign"] = sign
        gateway = settings.alipay_gateway.rstrip("/")
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(gateway, data=params)
        except httpx.HTTPError as exc:
            raise PaymentProviderError("ALIPAY_HTTP_ERROR", str(exc)) from exc
        if resp.status_code >= 400:
            raise PaymentProviderError(
                "ALIPAY_API_ERROR",
                f"Alipay precreate failed HTTP {resp.status_code}",
            )
        payload = resp.json()
        key = "alipay_trade_precreate_response"
        inner = payload.get(key) or {}
        if inner.get("code") != "10000":
            raise PaymentProviderError(
                "ALIPAY_API_ERROR",
                inner.get("sub_msg") or inner.get("msg") or "Alipay precreate rejected",
            )
        qr_code = inner.get("qr_code")
        if not qr_code:
            raise PaymentProviderError("ALIPAY_API_ERROR", "Alipay response missing qr_code")
        return CheckoutSession(checkout_url=None, qr_code_url=qr_code)

    def _sign_params(self, params: dict[str, str]) -> str:
        settings = self._settings()
        unsigned = "&".join(
            f"{k}={params[k]}"
            for k in sorted(params.keys())
            if params[k] and k != "sign"
        )
        private_key = load_private_key_pem(
            path=settings.alipay_private_key_path,
            content=settings.alipay_private_key,
        )
        return sign_sha256_rsa(unsigned, private_key)
