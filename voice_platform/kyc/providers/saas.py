"""Third-party KYC SaaS — async verify via HTTP submit + webhook callback."""

from __future__ import annotations

from uuid import UUID

import httpx

from voice_platform.config import get_settings
from voice_platform.kyc.providers.base import KycProviderError
from voice_platform.kyc.providers.base import KycProvider, KycSubmitResult


class SaasKycProvider(KycProvider):
    name = "saas"

    def submit(
        self,
        *,
        real_name: str,
        id_number: str,
        id_number_hash: str,
        user_id: UUID | None = None,
    ) -> KycSubmitResult:
        settings = get_settings()
        if not settings.kyc_saas_submit_url or not settings.kyc_saas_api_key:
            raise KycProviderError(
                "KYC_SAAS_NOT_CONFIGURED",
                "Set KYC_SAAS_SUBMIT_URL and KYC_SAAS_API_KEY",
            )
        if user_id is None:
            raise KycProviderError("KYC_USER_REQUIRED", "user_id required for SaaS KYC")

        body = {
            "user_id": str(user_id),
            "real_name": real_name,
            "id_number": id_number,
            "id_number_hash": id_number_hash,
        }
        headers = {
            "Authorization": f"Bearer {settings.kyc_saas_api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(settings.kyc_saas_submit_url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise KycProviderError("KYC_SAAS_HTTP_ERROR", str(exc)) from exc

        if resp.status_code >= 400:
            raise KycProviderError(
                "KYC_SAAS_API_ERROR",
                f"SaaS KYC submit failed HTTP {resp.status_code}: {resp.text[:200]}",
            )

        data = resp.json() if resp.content else {}
        external_ref = str(data.get("external_ref") or data.get("request_id") or "")
        message = data.get("message") or "Submitted to KYC SaaS; awaiting callback"
        if external_ref:
            message = f"{message} (ref={external_ref})"
        return KycSubmitResult(
            verified=False,
            status="pending",
            provider=self.name,
            message=message,
            external_ref=external_ref or None,
        )
