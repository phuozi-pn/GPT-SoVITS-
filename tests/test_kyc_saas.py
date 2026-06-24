"""KYC SaaS provider tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from voice_platform.kyc.providers import resolve_kyc_provider
from voice_platform.kyc.providers.saas import SaasKycProvider


def test_resolve_saas_when_configured():
    provider = resolve_kyc_provider(
        kyc_mock=False,
        kyc_provider="auto",
        kyc_saas_configured=True,
    )
    assert isinstance(provider, SaasKycProvider)


def test_saas_submit_pending():
    user_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"external_ref":"ref-1","message":"queued"}'
    mock_resp.json.return_value = {"external_ref": "ref-1", "message": "queued"}

    with (
        patch("voice_platform.kyc.providers.saas.get_settings") as gs,
        patch("voice_platform.kyc.providers.saas.httpx.Client") as client_cls,
    ):
        gs.return_value.kyc_saas_submit_url = "https://kyc.example/verify"
        gs.return_value.kyc_saas_api_key = "key"
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        result = SaasKycProvider().submit(
            real_name="张三",
            id_number="110101199001011234",
            id_number_hash="hash",
            user_id=user_id,
        )
    assert result.verified is False
    assert result.status == "pending"
    assert "ref-1" in result.message
