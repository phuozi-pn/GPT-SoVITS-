"""Mock KYC — instant pass for local dev."""

from __future__ import annotations

from voice_platform.kyc.providers.base import KycProvider, KycSubmitResult


class MockKycProvider(KycProvider):
    name = "mock"

    def submit(
        self,
        *,
        real_name: str,
        id_number: str,
        id_number_hash: str,
        user_id=None,
    ) -> KycSubmitResult:
        return KycSubmitResult(
            verified=True,
            status="approved",
            provider=self.name,
            message="Real-name verification passed (mock)",
        )
