"""KYC provider registry."""

from __future__ import annotations

from voice_platform.kyc.providers.base import KycProvider, KycProviderError
from voice_platform.kyc.providers.manual import ManualPendingKycProvider
from voice_platform.kyc.providers.mock import MockKycProvider
from voice_platform.kyc.providers.saas import SaasKycProvider

_PROVIDERS: dict[str, type[KycProvider]] = {
    "mock": MockKycProvider,
    "manual": ManualPendingKycProvider,
    "saas": SaasKycProvider,
}


def resolve_kyc_provider(
    *,
    kyc_mock: bool,
    kyc_provider: str,
    kyc_saas_configured: bool = False,
) -> KycProvider:
    if kyc_provider == "auto":
        if kyc_mock:
            name = "mock"
        elif kyc_saas_configured:
            name = "saas"
        else:
            name = "manual"
    else:
        name = kyc_provider
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise KycProviderError("UNKNOWN_PROVIDER", f"Unknown KYC provider: {name}")
    return cls()
