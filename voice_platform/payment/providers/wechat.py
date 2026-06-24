"""WeChat Pay Native pre-order (API v3)."""

from __future__ import annotations

import json
import time
from uuid import uuid4

import httpx

from voice_platform.config import get_settings
from voice_platform.payment.providers._rsa import load_private_key_pem, sign_sha256_rsa
from voice_platform.payment.providers.base import (
    CheckoutOrderContext,
    CheckoutSession,
    PaymentProvider,
    PaymentProviderError,
)


class WechatPaymentProvider(PaymentProvider):
    name = "wechat"

    def _settings(self):
        return get_settings()

    def _ensure_config(self) -> None:
        s = self._settings()
        missing = [
            name
            for name, val in (
                ("WECHAT_PAY_APP_ID", s.wechat_pay_app_id),
                ("WECHAT_PAY_MCH_ID", s.wechat_pay_mch_id),
                ("WECHAT_PAY_SERIAL", s.wechat_pay_serial),
            )
            if not val
        ]
        if missing:
            raise PaymentProviderError(
                "WECHAT_NOT_CONFIGURED",
                f"WeChat Pay missing env: {', '.join(missing)}",
            )
        if not (s.wechat_pay_private_key or s.wechat_pay_private_key_path):
            raise PaymentProviderError(
                "WECHAT_NOT_CONFIGURED",
                "Set WECHAT_PAY_PRIVATE_KEY or WECHAT_PAY_PRIVATE_KEY_PATH",
            )
        if not s.payment_notify_base_url:
            raise PaymentProviderError(
                "WECHAT_NOT_CONFIGURED",
                "Set PAYMENT_NOTIFY_BASE_URL for WeChat notify_url",
            )

    def create_checkout(self, order: CheckoutOrderContext) -> CheckoutSession:
        self._ensure_config()
        settings = self._settings()
        path = "/v3/pay/transactions/native"
        url = f"{settings.wechat_pay_api_base.rstrip('/')}{path}"
        notify_url = f"{settings.payment_notify_base_url.rstrip('/')}/api/v1/payments/webhooks/wechat"
        body_obj = {
            "appid": settings.wechat_pay_app_id,
            "mchid": settings.wechat_pay_mch_id,
            "description": order.catalog_title[:127] or "Voice catalog purchase",
            "out_trade_no": order.provider_ref,
            "notify_url": notify_url,
            "amount": {"total": order.amount_cents, "currency": order.currency.upper()},
        }
        body = json.dumps(body_obj, ensure_ascii=False, separators=(",", ":"))
        headers = self._auth_headers(method="POST", path=path, body=body)
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, content=body.encode("utf-8"), headers=headers)
        except httpx.HTTPError as exc:
            raise PaymentProviderError("WECHAT_HTTP_ERROR", str(exc)) from exc
        if resp.status_code >= 400:
            raise PaymentProviderError(
                "WECHAT_API_ERROR",
                f"WeChat pre-order failed HTTP {resp.status_code}: {resp.text[:300]}",
            )
        data = resp.json()
        code_url = data.get("code_url")
        if not code_url:
            raise PaymentProviderError("WECHAT_API_ERROR", "WeChat response missing code_url")
        return CheckoutSession(checkout_url=None, qr_code_url=code_url)

    def _auth_headers(self, *, method: str, path: str, body: str) -> dict[str, str]:
        settings = self._settings()
        timestamp = str(int(time.time()))
        nonce = uuid4().hex
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
        private_key = load_private_key_pem(
            path=settings.wechat_pay_private_key_path,
            content=settings.wechat_pay_private_key,
        )
        signature = sign_sha256_rsa(message, private_key)
        token = (
            f'WECHATPAY2-SHA256-RSA2048 mchid="{settings.wechat_pay_mch_id}",'
            f'nonce_str="{nonce}",timestamp="{timestamp}",'
            f'serial_no="{settings.wechat_pay_serial}",signature="{signature}"'
        )
        return {
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phonia-Voice-Platform/1.0",
        }
