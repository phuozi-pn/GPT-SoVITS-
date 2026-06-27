"""Resend email client tests."""

from unittest.mock import MagicMock, patch

import httpx

from voice_platform.email.resend import ResendClient, ResendError


def test_resend_send_login_code_ok():
    with (
        patch("voice_platform.email.resend.get_settings") as settings_cls,
        patch("voice_platform.email.resend.httpx.Client") as client_cls,
    ):
        settings = settings_cls.return_value
        settings.resend_api_key = "re_test"
        settings.resend_from_email = "Phonia <onboarding@resend.dev>"
        settings.resend_api_base = "https://api.resend.com"

        resp = MagicMock(status_code=200, text="{}")
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = resp

        ResendClient().send_login_code(to_email="user@example.com", code="123456", ttl_minutes=5)

    client.post.assert_called_once()
    payload = client.post.call_args.kwargs["json"]
    assert payload["to"] == ["user@example.com"]
    assert "123456" in payload["subject"]


def test_resend_send_login_code_api_error():
    with (
        patch("voice_platform.email.resend.get_settings") as settings_cls,
        patch("voice_platform.email.resend.httpx.Client") as client_cls,
    ):
        settings = settings_cls.return_value
        settings.resend_api_key = "re_test"
        settings.resend_from_email = "Phonia <onboarding@resend.dev>"
        settings.resend_api_base = "https://api.resend.com"

        resp = MagicMock(status_code=422, text='{"message":"invalid from"}')
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = resp

        try:
            ResendClient().send_login_code(to_email="user@example.com", code="123456", ttl_minutes=5)
            assert False, "expected ResendError"
        except ResendError as exc:
            assert exc.code == "RESEND_API_ERROR"
