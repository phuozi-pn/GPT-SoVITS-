"""REQ-002 real-name verification (mock provider + admin override)."""

from __future__ import annotations

import hashlib
import hmac
import json
from uuid import UUID

from voice_platform.auth.repository import UserRepository
from voice_platform.config import get_settings
from voice_platform.kyc.id_card import hash_id_number, is_adult, is_valid_id_format, mask_real_name
from voice_platform.kyc.providers import resolve_kyc_provider
from voice_platform.kyc.repository import KycAuditRepository
from voice_platform.kyc.schemas import KycAuditEntry, KycStatusResponse, KycSubmitResponse


class KycServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class KycService:
    def __init__(self, session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._audit = KycAuditRepository(session)
        self._settings = get_settings()

    def get_status(self, user_id: UUID) -> KycStatusResponse:
        user = self._users.get_by_id(user_id)
        if not user:
            raise KycServiceError("USER_NOT_FOUND", "User not found", 404)
        return KycStatusResponse(
            verified=user.verified,
            verified_at=user.verified_at,
            required=self._settings.kyc_required,
            provider=resolve_kyc_provider(
                kyc_mock=self._settings.kyc_mock,
                kyc_provider=self._settings.kyc_provider,
                kyc_saas_configured=self._settings.kyc_saas_configured,
            ).name,
        )

    def ensure_verified_for_train(self, user_id: UUID) -> None:
        if not self._settings.kyc_required:
            return
        user = self._users.get_by_id(user_id)
        if not user or not user.verified:
            raise KycServiceError(
                "KYC_REQUIRED",
                "Real-name verification required before training",
                403,
            )

    def submit(self, user_id: UUID, *, real_name: str, id_number: str) -> KycSubmitResponse:
        user = self._users.get_by_id(user_id)
        if not user:
            raise KycServiceError("USER_NOT_FOUND", "User not found", 404)
        if user.verified:
            return KycSubmitResponse(
                verified=True,
                message="Already verified",
                audit_id=self._audit.append(
                    user_id=user_id,
                    action="submit",
                    status="approved",
                    message="duplicate submit ignored",
                    real_name_masked=mask_real_name(real_name),
                    id_number_last4=id_number[-4:],
                    id_number_hash=hash_id_number(id_number),
                ).id,
            )

        if not is_valid_id_format(id_number):
            self._audit.append(
                user_id=user_id,
                action="submit",
                status="rejected",
                message="Invalid ID number format",
                real_name_masked=mask_real_name(real_name),
                id_number_last4=id_number[-4:],
                id_number_hash=hash_id_number(id_number),
            )
            raise KycServiceError(
                "KYC_INVALID_ID",
                "Invalid ID number format",
                422,
            )

        if not is_adult(id_number):
            self._audit.append(
                user_id=user_id,
                action="submit",
                status="rejected",
                message="Minor ID rejected",
                real_name_masked=mask_real_name(real_name),
                id_number_last4=id_number[-4:],
                id_number_hash=hash_id_number(id_number),
            )
            raise KycServiceError(
                "KYC_MINOR_NOT_ALLOWED",
                "Minors cannot train voices; guardian flow not supported in MVP",
                403,
            )

        id_hash = hash_id_number(id_number)
        provider = resolve_kyc_provider(
            kyc_mock=self._settings.kyc_mock,
            kyc_provider=self._settings.kyc_provider,
            kyc_saas_configured=self._settings.kyc_saas_configured,
        )
        try:
            result = provider.submit(
                real_name=real_name,
                id_number=id_number,
                id_number_hash=id_hash,
                user_id=user_id,
            )
        except Exception as exc:
            from voice_platform.kyc.providers.base import KycProviderError

            if isinstance(exc, KycProviderError):
                raise KycServiceError(exc.code, exc.message, 503) from exc
            raise

        if result.verified:
            self._users.set_verified(user_id, verified=True, id_number_hash=id_hash)
        audit = self._audit.append(
            user_id=user_id,
            action="submit",
            status=result.status,
            provider=result.provider,
            message=result.message,
            real_name_masked=mask_real_name(real_name),
            id_number_last4=id_number[-4:],
            id_number_hash=id_hash,
        )
        return KycSubmitResponse(
            verified=result.verified,
            message=result.message,
            audit_id=audit.id,
        )

    def admin_verify(self, user_id: UUID, *, note: str | None = None) -> KycStatusResponse:
        user = self._users.get_by_id(user_id)
        if not user:
            raise KycServiceError("USER_NOT_FOUND", "User not found", 404)
        self._users.set_verified(user_id, verified=True)
        self._audit.append(
            user_id=user_id,
            action="admin_verify",
            status="approved",
            message=note or "Manual verification by operator",
        )
        return self.get_status(user_id)

    def admin_revoke(self, user_id: UUID, *, note: str | None = None) -> KycStatusResponse:
        user = self._users.get_by_id(user_id)
        if not user:
            raise KycServiceError("USER_NOT_FOUND", "User not found", 404)
        self._users.set_verified(user_id, verified=False, clear_id_hash=True)
        self._audit.append(
            user_id=user_id,
            action="admin_revoke",
            status="rejected",
            message=note or "Verification revoked by operator",
        )
        return self.get_status(user_id)

    def process_saas_webhook(self, *, body: bytes, signature: str | None) -> KycStatusResponse:
        secret = (self._settings.kyc_saas_webhook_secret or "").strip()
        if secret:
            expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature.strip()):
                raise KycServiceError("WEBHOOK_SIGNATURE_INVALID", "Invalid KYC webhook signature", 401)

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise KycServiceError("INVALID_PAYLOAD", "Invalid JSON body", 400) from exc

        user_id_raw = data.get("user_id")
        if not user_id_raw:
            raise KycServiceError("INVALID_PAYLOAD", "user_id required", 400)
        user_id = UUID(str(user_id_raw))
        user = self._users.get_by_id(user_id)
        if not user:
            raise KycServiceError("USER_NOT_FOUND", "User not found", 404)

        status = str(data.get("status", "")).lower()
        note = str(data.get("note") or data.get("message") or "KYC SaaS callback")
        if status in ("approved", "verified", "pass"):
            id_hash = data.get("id_number_hash")
            self._users.set_verified(
                user_id,
                verified=True,
                id_number_hash=str(id_hash) if id_hash else None,
            )
            self._audit.append(
                user_id=user_id,
                action="saas_webhook",
                status="approved",
                provider="saas",
                message=note,
            )
        elif status in ("rejected", "failed"):
            self._audit.append(
                user_id=user_id,
                action="saas_webhook",
                status="rejected",
                provider="saas",
                message=note,
            )
        else:
            raise KycServiceError("UNSUPPORTED_STATUS", f"Unsupported status: {status}", 400)
        return self.get_status(user_id)

    def list_audit(self, user_id: UUID) -> list[KycAuditEntry]:
        rows = self._audit.list_for_user(user_id)
        return [
            KycAuditEntry(
                audit_id=r.id,
                user_id=r.user_id,
                action=r.action,
                status=r.status,
                provider=r.provider,
                message=r.message,
                real_name_masked=r.real_name_masked,
                id_number_last4=r.id_number_last4,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def list_pending_users(self, *, limit: int = 50) -> list:
        from voice_platform.kyc.schemas import AdminKycUserSummary

        rows = self._users.list_by_verified(verified=False, limit=limit)
        return [
            AdminKycUserSummary(
                user_id=r.id,
                phone=r.phone,
                verified=r.verified,
                verified_at=r.verified_at,
                created_at=r.created_at,
            )
            for r in rows
        ]
