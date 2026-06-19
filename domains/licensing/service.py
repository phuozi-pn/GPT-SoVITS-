from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from voice_platform.config import get_settings
from voice_platform.job.repository import (
    PaymentOrderRepository,
    VoiceAuthorizationRepository,
    VoiceCatalogRepository,
    VoiceComplaintRepository,
    VoiceRepository,
    VoiceVersionRepository,
)
from voice_platform.job.schemas import (
    AuthorizationCertificateResponse,
    AuthorizationResponse,
    AuthorizationVerifyResponse,
    CatalogEntryResponse,
    CatalogLicensePolicyRequest,
    ComplaintCreateRequest,
    ComplaintResponse,
    PaymentOrderResponse,
)

from domains.voices.access import user_can_access_voice_version
from voice_platform.social.system import send_system_notice


class LicensingServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class LicensingService:
    def __init__(self, session) -> None:
        self._session = session
        self._catalog = VoiceCatalogRepository(session)
        self._auths = VoiceAuthorizationRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._voices = VoiceRepository(session)
        self._complaints = VoiceComplaintRepository(session)
        self._payments = PaymentOrderRepository(session)

    def _auth_response(self, row, *, voice_title: str) -> AuthorizationResponse:
        remaining = max(0, row.char_quota_total - row.char_quota_used)
        return AuthorizationResponse(
            authorization_id=row.id,
            catalog_id=row.catalog_id,
            voice_version_id=row.voice_version_id,
            voice_id=row.voice_id,
            voice_title=voice_title,
            seller_user_id=row.seller_user_id,
            buyer_user_id=row.buyer_user_id,
            license_type=row.license_type,
            billing_unit=row.billing_unit,
            char_quota_total=row.char_quota_total,
            char_quota_used=row.char_quota_used,
            char_quota_remaining=remaining,
            price_paid_cents=row.price_paid_cents,
            payment_ref=row.payment_ref,
            status=row.status,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    def update_license_policy(
        self,
        *,
        catalog_id: UUID,
        owner_user_id: UUID,
        body: CatalogLicensePolicyRequest,
    ) -> CatalogEntryResponse:
        from domains.marketplace.service import MarketplaceService

        row = self._catalog.update_license_policy(
            catalog_id,
            owner_user_id=owner_user_id,
            license_type=body.license_type,
            price_cents=body.price_cents,
            billing_unit=body.billing_unit,
            included_chars=body.included_chars,
            prohibited_domains=body.prohibited_domains,
        )
        if not row:
            raise LicensingServiceError("CATALOG_NOT_FOUND", "Catalog entry not found", 404)
        item = MarketplaceService(self._session)._entry_response(
            row,
            viewer_user_id=owner_user_id,
        )
        if not item:
            raise LicensingServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        return item

    def purchase(
        self,
        *,
        catalog_id: UUID,
        buyer_user_id: UUID,
    ) -> AuthorizationResponse:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise LicensingServiceError("CATALOG_NOT_FOUND", "Published catalog entry not found", 404)
        if entry.owner_user_id == buyer_user_id:
            raise LicensingServiceError("INVALID_BUYER", "Owner does not need to purchase", 400)
        ver = self._versions.get(entry.voice_version_id)
        if not ver:
            raise LicensingServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        if self._auths.has_active_for_voice(
            buyer_user_id=buyer_user_id,
            voice_version_id=entry.voice_version_id,
        ):
            active = self._auths.get_active_for_voice(
                buyer_user_id=buyer_user_id,
                voice_version_id=entry.voice_version_id,
            )
            if active:
                return self._auth_response(active, voice_title=entry.title)

        settings = get_settings()
        if settings.payment_checkout_async and entry.price_cents > 0:
            raise LicensingServiceError(
                "CHECKOUT_REQUIRED",
                "Use POST /catalog/voices/{id}/checkout for paid voices",
                409,
            )

        row = self._fulfill_catalog_purchase(
            entry=entry,
            ver=ver,
            buyer_user_id=buyer_user_id,
            payment_ref=f"mock_pay_{uuid4().hex[:12]}",
        )
        return self._auth_response(row, voice_title=entry.title)

    def _create_authorization(
        self,
        *,
        entry,
        ver,
        buyer_user_id: UUID,
        payment_ref: str,
    ):
        expires_at = None
        if entry.billing_unit == "monthly_flat":
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        return self._auths.create_purchase(
            catalog_id=entry.id,
            voice_version_id=entry.voice_version_id,
            voice_id=ver.voice_id,
            seller_user_id=entry.owner_user_id,
            buyer_user_id=buyer_user_id,
            license_type=entry.license_type,
            billing_unit=entry.billing_unit,
            char_quota_total=entry.included_chars,
            price_paid_cents=entry.price_cents,
            payment_ref=payment_ref,
            expires_at=expires_at,
        )

    def _fulfill_catalog_purchase(
        self,
        *,
        entry,
        ver,
        buyer_user_id: UUID,
        payment_ref: str,
    ):
        settings = get_settings()
        row = self._create_authorization(
            entry=entry,
            ver=ver,
            buyer_user_id=buyer_user_id,
            payment_ref=payment_ref,
        )
        order = self._payments.create(
            authorization_id=row.id,
            catalog_id=entry.id,
            buyer_user_id=buyer_user_id,
            seller_user_id=entry.owner_user_id,
            amount_cents=entry.price_cents,
            provider=settings.payment_provider,
            provider_ref=payment_ref,
            status="paid",
            paid_at=datetime.now(timezone.utc),
        )
        from domains.settlement.service import SettlementService

        SettlementService(self._session).credit_from_payment_order(order)

        title = entry.title
        send_system_notice(
            self._session,
            recipient_user_id=buyer_user_id,
            conversation_peer_user_id=entry.owner_user_id,
            body=f"【系统】你已购买「{title}」，授权已发放。可在音色馆下载样音/音色包，或在工作台直接使用。",
        )
        send_system_notice(
            self._session,
            recipient_user_id=entry.owner_user_id,
            conversation_peer_user_id=buyer_user_id,
            body=f"【系统】你的音色「{title}」产生一笔购买，授权已自动发放给买家。",
        )
        return row

    def create_authorization_for_payment(
        self,
        *,
        catalog_id: UUID,
        buyer_user_id: UUID,
        payment_ref: str,
    ) -> AuthorizationResponse:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise LicensingServiceError("CATALOG_NOT_FOUND", "Published catalog entry not found", 404)
        if entry.owner_user_id == buyer_user_id:
            raise LicensingServiceError("INVALID_BUYER", "Owner does not need to purchase", 400)
        ver = self._versions.get(entry.voice_version_id)
        if not ver:
            raise LicensingServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        if self._auths.has_active_for_voice(
            buyer_user_id=buyer_user_id,
            voice_version_id=entry.voice_version_id,
        ):
            active = self._auths.get_active_for_voice(
                buyer_user_id=buyer_user_id,
                voice_version_id=entry.voice_version_id,
            )
            if active:
                return self._auth_response(active, voice_title=entry.title)
        row = self._create_authorization(
            entry=entry,
            ver=ver,
            buyer_user_id=buyer_user_id,
            payment_ref=payment_ref,
        )
        return self._auth_response(row, voice_title=entry.title)

    def list_purchases(self, *, buyer_user_id: UUID) -> list[AuthorizationResponse]:
        out: list[AuthorizationResponse] = []
        for row in self._auths.list_for_buyer(buyer_user_id):
            entry = self._catalog.get(row.catalog_id)
            title = entry.title if entry else "unknown"
            out.append(self._auth_response(row, voice_title=title))
        return out

    def list_sales(self, *, seller_user_id: UUID) -> list[AuthorizationResponse]:
        out: list[AuthorizationResponse] = []
        for row in self._auths.list_for_seller(seller_user_id):
            entry = self._catalog.get(row.catalog_id)
            title = entry.title if entry else "unknown"
            out.append(self._auth_response(row, voice_title=title))
        return out

    def get_certificate(self, *, authorization_id: UUID, user_id: UUID) -> AuthorizationCertificateResponse:
        row = self._auths.get(authorization_id)
        if not row:
            raise LicensingServiceError("AUTH_NOT_FOUND", "Authorization not found", 404)
        if user_id not in (row.buyer_user_id, row.seller_user_id):
            raise LicensingServiceError("AUTH_FORBIDDEN", "Not your authorization", 403)
        entry = self._catalog.get(row.catalog_id)
        payload = {
            "authorization_id": str(row.id),
            "seller_user_id": str(row.seller_user_id),
            "buyer_user_id": str(row.buyer_user_id),
            "voice_version_id": str(row.voice_version_id),
            "catalog_id": str(row.catalog_id),
            "license_type": row.license_type,
            "char_quota_total": row.char_quota_total,
            "char_quota_used": row.char_quota_used,
            "status": row.status,
            "issued_at": row.created_at.isoformat() if row.created_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }
        secret = get_settings().jwt_secret
        signature = hmac.new(
            secret.encode(),
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode(),
            hashlib.sha256,
        ).hexdigest()
        return AuthorizationCertificateResponse(
            authorization_id=row.id,
            seller_user_id=row.seller_user_id,
            buyer_user_id=row.buyer_user_id,
            voice_version_id=row.voice_version_id,
            catalog_id=row.catalog_id,
            voice_title=entry.title if entry else "unknown",
            license_type=row.license_type,
            char_quota_total=row.char_quota_total,
            char_quota_used=row.char_quota_used,
            status=row.status,
            issued_at=row.created_at,
            expires_at=row.expires_at,
            signature=signature,
        )

    def verify_certificate(self, authorization_id: UUID) -> AuthorizationVerifyResponse:
        row = self._auths.get(authorization_id)
        if not row:
            return AuthorizationVerifyResponse(
                authorization_id=authorization_id,
                status="not_found",
                valid=False,
                voice_title="",
                license_type="",
                message="Authorization not found",
            )
        entry = self._catalog.get(row.catalog_id)
        valid = row.status == "active"
        if valid and row.expires_at and row.expires_at < datetime.now(timezone.utc):
            valid = False
        if valid and row.char_quota_total > 0 and row.char_quota_used >= row.char_quota_total:
            valid = False
        msg = "有效" if valid else f"无效（{row.status}）"
        return AuthorizationVerifyResponse(
            authorization_id=row.id,
            status=row.status,
            valid=valid,
            voice_title=entry.title if entry else "unknown",
            license_type=row.license_type,
            message=msg,
        )

    def check_project_domain(
        self,
        *,
        voice_version_id: UUID,
        project_type: str | None,
    ) -> None:
        if not project_type:
            return
        entry = self._catalog.get_by_version(voice_version_id)
        if not entry:
            return
        blocked = {str(d).strip().lower() for d in (entry.prohibited_domains_json or [])}
        if project_type.strip().lower() in blocked:
            raise LicensingServiceError(
                "DOMAIN_PROHIBITED",
                f"Project type '{project_type}' is prohibited for this voice license",
                403,
            )

    def ensure_purchase_quota(
        self,
        *,
        user_id: UUID,
        voice_version_id: UUID,
        char_count: int,
    ) -> None:
        entry = self._catalog.get_by_version(voice_version_id)
        if not entry or entry.price_cents <= 0:
            return
        if entry.owner_user_id == user_id:
            return
        auth = self._auths.get_active_for_voice(
            buyer_user_id=user_id,
            voice_version_id=voice_version_id,
        )
        if not auth:
            raise LicensingServiceError(
                "PURCHASE_REQUIRED",
                "Purchase authorization required for this paid voice",
                403,
            )
        if auth.char_quota_total > 0 and auth.char_quota_used + char_count > auth.char_quota_total:
            raise LicensingServiceError(
                "AUTH_QUOTA_EXCEEDED",
                "Authorization character quota exceeded",
                403,
            )

    def record_synthesis_usage(
        self,
        *,
        user_id: UUID,
        payload: InferPayload,
    ) -> None:
        if payload.segments:
            for seg in payload.segments:
                self._record_voice_usage(user_id=user_id, voice_version_id=seg.voice_version_id, chars=len(seg.text))
        elif payload.voice_version_id:
            self._record_voice_usage(
                user_id=user_id,
                voice_version_id=payload.voice_version_id,
                chars=payload.billed_char_count(),
            )

    def _record_voice_usage(self, *, user_id: UUID, voice_version_id: UUID, chars: int) -> None:
        entry = self._catalog.get_by_version(voice_version_id)
        if not entry or entry.price_cents <= 0 or entry.owner_user_id == user_id:
            return
        auth = self._auths.get_active_for_voice(
            buyer_user_id=user_id,
            voice_version_id=voice_version_id,
        )
        if auth:
            self._auths.record_chars(auth.id, chars)

    def submit_complaint(
        self,
        *,
        reporter_user_id: UUID,
        body: ComplaintCreateRequest,
    ) -> ComplaintResponse:
        if not body.catalog_id and not body.voice_version_id:
            raise LicensingServiceError(
                "COMPLAINT_TARGET_REQUIRED",
                "catalog_id or voice_version_id required",
                400,
            )
        row = self._complaints.create(
            reporter_user_id=reporter_user_id,
            description=body.description,
            target_url=body.target_url,
            catalog_id=body.catalog_id,
            voice_version_id=body.voice_version_id,
            evidence=body.evidence_urls,
        )
        return self._complaint_response(row)

    def list_payment_orders(self, *, limit: int = 50) -> list[PaymentOrderResponse]:
        return [
            PaymentOrderResponse(
                order_id=r.id,
                authorization_id=r.authorization_id,
                catalog_id=r.catalog_id,
                buyer_user_id=r.buyer_user_id,
                seller_user_id=r.seller_user_id,
                amount_cents=r.amount_cents,
                currency=r.currency,
                status=r.status,
                provider=r.provider,
                provider_ref=r.provider_ref,
                paid_at=r.paid_at,
                created_at=r.created_at,
            )
            for r in self._payments.list_recent(limit=limit)
        ]

    def list_open_complaints(self) -> list[ComplaintResponse]:
        return [self._complaint_response(r) for r in self._complaints.list_open()]

    def takedown_complaint(
        self,
        *,
        complaint_id: UUID,
        admin_user_id: UUID,
        resolution_note: str,
    ) -> ComplaintResponse:
        row = self._complaints.get(complaint_id)
        if not row or row.status != "open":
            raise LicensingServiceError("COMPLAINT_NOT_FOUND", "Open complaint not found", 404)
        catalog_id = row.catalog_id
        if not catalog_id and row.voice_version_id:
            entry = self._catalog.get_by_version(row.voice_version_id)
            catalog_id = entry.id if entry else None
        if catalog_id:
            self._catalog.takedown(catalog_id)
            self._auths.revoke_for_catalog(catalog_id)
        resolved = self._complaints.resolve(
            complaint_id,
            resolved_by=admin_user_id,
            status="resolved",
            resolution_note=resolution_note or "Takedown completed",
        )
        if not resolved:
            raise LicensingServiceError("COMPLAINT_NOT_FOUND", "Complaint not found", 404)
        return self._complaint_response(resolved)

    def dismiss_complaint(
        self,
        *,
        complaint_id: UUID,
        admin_user_id: UUID,
        resolution_note: str,
    ) -> ComplaintResponse:
        resolved = self._complaints.resolve(
            complaint_id,
            resolved_by=admin_user_id,
            status="dismissed",
            resolution_note=resolution_note or "Dismissed",
        )
        if not resolved:
            raise LicensingServiceError("COMPLAINT_NOT_FOUND", "Open complaint not found", 404)
        return self._complaint_response(resolved)

    def build_certificate_pdf(self, *, authorization_id: UUID, user_id: UUID) -> bytes:
        """Generate a PDF certificate for the given authorization."""
        from voice_platform.licensing.certificate_pdf import build_authorization_pdf

        cert = self.get_certificate(authorization_id=authorization_id, user_id=user_id)
        return build_authorization_pdf(cert)

    @staticmethod
    def _complaint_response(row) -> ComplaintResponse:
        return ComplaintResponse(
            complaint_id=row.id,
            catalog_id=row.catalog_id,
            voice_version_id=row.voice_version_id,
            reporter_user_id=row.reporter_user_id,
            target_url=row.target_url,
            description=row.description,
            evidence_urls=list(row.evidence_json or []),
            status=row.status,
            resolution_note=row.resolution_note,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
        )


def catalog_entry_can_use(session, entry, viewer_user_id: UUID) -> bool:
    if entry.status != "published":
        return False
    return user_can_access_voice_version(session, entry.voice_version_id, viewer_user_id)


def catalog_entry_purchased(session, entry, viewer_user_id: UUID) -> bool:
    if entry.price_cents <= 0:
        return False
    auths = VoiceAuthorizationRepository(session)
    return auths.has_active_for_voice(
        buyer_user_id=viewer_user_id,
        voice_version_id=entry.voice_version_id,
    )
