"""KYC provider registry tests."""

from __future__ import annotations

from voice_platform.kyc.providers import resolve_kyc_provider
from voice_platform.kyc.providers.manual import ManualPendingKycProvider
from voice_platform.kyc.providers.mock import MockKycProvider


def test_resolve_mock_when_kyc_mock_true():
    provider = resolve_kyc_provider(kyc_mock=True, kyc_provider="auto")
    assert isinstance(provider, MockKycProvider)
    result = provider.submit(real_name="张三", id_number="110101199001011234", id_number_hash="abc")
    assert result.verified is True
    assert result.status == "approved"


def test_resolve_manual_when_kyc_mock_false():
    provider = resolve_kyc_provider(
        kyc_mock=False,
        kyc_provider="auto",
        kyc_saas_configured=False,
    )
    assert isinstance(provider, ManualPendingKycProvider)
    result = provider.submit(real_name="张三", id_number="110101199001011234", id_number_hash="abc")
    assert result.verified is False
    assert result.status == "pending"
