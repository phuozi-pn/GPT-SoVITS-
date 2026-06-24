"""Manual pending KYC — operator review via /admin/kyc."""

from __future__ import annotations

from voice_platform.kyc.providers.base import KycProvider, KycSubmitResult


class ManualPendingKycProvider(KycProvider):
    name = "manual"

    def submit(
        self,
        *,
        real_name: str,
        id_number: str,
        id_number_hash: str,
        user_id=None,
    ) -> KycSubmitResult:
        return KycSubmitResult(
            verified=False,
            status="pending",
            provider=self.name,
            message="Submitted for manual review; training unlocks after operator approval",
        )
