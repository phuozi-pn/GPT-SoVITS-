"""Resend transactional email — login OTP."""

from __future__ import annotations

import httpx

from voice_platform.config import get_settings


class ResendError(Exception):
    def __init__(self, message: str, *, code: str = "RESEND_ERROR") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ResendClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.resend_api_key
        self._from_email = settings.resend_from_email
        self._base = settings.resend_api_base.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self._api_key and self._from_email)

    def send_login_code(self, *, to_email: str, code: str, ttl_minutes: int) -> None:
        if not self.enabled:
            raise ResendError("未配置 RESEND_API_KEY / RESEND_FROM_EMAIL", code="RESEND_NOT_CONFIGURED")

        subject = f"Phonia 登录验证码 {code}"
        html = (
            f"<p>您的 Phonia 登录验证码是：<strong style=\"font-size:20px;letter-spacing:2px\">{code}</strong></p>"
            f"<p>验证码 {ttl_minutes} 分钟内有效，请勿泄露给他人。</p>"
            f"<p style=\"color:#888;font-size:12px\">如非本人操作，请忽略此邮件。</p>"
        )
        text = f"您的 Phonia 登录验证码是：{code}（{ttl_minutes} 分钟内有效）"

        payload = {
            "from": self._from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self._base}/emails",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ResendError(f"Resend 请求失败: {exc}", code="RESEND_HTTP_ERROR") from exc

        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise ResendError(f"Resend 发信失败 ({resp.status_code}): {detail}", code="RESEND_API_ERROR")
