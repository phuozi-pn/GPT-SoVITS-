"""Checkout, webhook fulfillment, and mock confirm."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from domains.licensing.service import LicensingService, LicensingServiceError
from domains.settlement.service import SettlementService
from voice_platform.config import get_settings
from voice_platform.job.repository import PaymentOrderRepository, VoiceCatalogRepository
from voice_platform.payment.models import PaymentWebhookEventRow
from voice_platform.payment.schemas import (
    CheckoutResponse,
    MockPaymentConfirmResponse,
    PaymentOrderStatusResponse,
    PaymentWebhookPayload,
)
from voice_platform.payment.webhook import new_provider_ref, verify_webhook_signature


class PaymentServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class PaymentService:
    def __init__(self, session) -> None:
        self._session = session
        self._orders = PaymentOrderRepository(session)
        self._catalog = VoiceCatalogRepository(session)
        self._licensing = LicensingService(session)
        self._settings = get_settings()

    def _order_status(self, row) -> PaymentOrderStatusResponse:
        return PaymentOrderStatusResponse(
            order_id=row.id,
            status=row.status,
            amount_cents=row.amount_cents,
            provider=row.provider,
            provider_ref=row.provider_ref,
            authorization_id=row.authorization_id,
            paid_at=row.paid_at,
            created_at=row.created_at,
        )

    def checkout(self, *, catalog_id: UUID, buyer_user_id: UUID) -> CheckoutResponse:
        entry = self._catalog.get(catalog_id)
        if not entry or entry.status != "published":
            raise PaymentServiceError("CATALOG_NOT_FOUND", "Published catalog entry not found", 404)
        if entry.owner_user_id == buyer_user_id:
            raise PaymentServiceError("INVALID_BUYER", "Owner does not need to purchase", 400)

        provider_ref = new_provider_ref(prefix="chk")
        provider = self._settings.payment_provider

        if entry.price_cents <= 0:
            try:
                auth = self._licensing.create_authorization_for_payment(
                    catalog_id=catalog_id,
                    buyer_user_id=buyer_user_id,
                    payment_ref=provider_ref,
                )
            except LicensingServiceError as exc:
                raise PaymentServiceError(exc.code, exc.message, exc.http_status) from exc
            order = self._orders.create(
                authorization_id=auth.authorization_id,
                catalog_id=catalog_id,
                buyer_user_id=buyer_user_id,
                seller_user_id=entry.owner_user_id,
                amount_cents=0,
                provider=provider,
                provider_ref=provider_ref,
                status="paid",
                paid_at=datetime.now(timezone.utc),
            )
            SettlementService(self._session).credit_from_payment_order(order)
            return CheckoutResponse(
                order_id=order.id,
                status="paid",
                amount_cents=0,
                currency=order.currency,
                provider=provider,
                provider_ref=provider_ref,
                authorization_id=auth.authorization_id,
            )

        order = self._orders.create(
            authorization_id=None,
            catalog_id=catalog_id,
            buyer_user_id=buyer_user_id,
            seller_user_id=entry.owner_user_id,
            amount_cents=entry.price_cents,
            provider=provider,
            provider_ref=provider_ref,
            status="pending",
        )
        checkout_url = f"/api/v1/payments/orders/{order.id}/mock-confirm"
        return CheckoutResponse(
            order_id=order.id,
            status="pending",
            amount_cents=entry.price_cents,
            currency=order.currency,
            provider=provider,
            provider_ref=provider_ref,
            checkout_url=checkout_url if provider == "mock" else None,
        )

    def get_order(self, *, order_id: UUID, buyer_user_id: UUID) -> PaymentOrderStatusResponse:
        row = self._orders.get(order_id)
        if not row or row.buyer_user_id != buyer_user_id:
            raise PaymentServiceError("ORDER_NOT_FOUND", "Payment order not found", 404)
        return self._order_status(row)

    def mock_confirm(self, *, order_id: UUID, buyer_user_id: UUID) -> MockPaymentConfirmResponse:
        if self._settings.payment_provider != "mock":
            raise PaymentServiceError("MOCK_ONLY", "Mock confirm only for mock provider", 400)
        row = self._orders.get(order_id)
        if not row or row.buyer_user_id != buyer_user_id:
            raise PaymentServiceError("ORDER_NOT_FOUND", "Payment order not found", 404)
        auth = self._fulfill_pending_order(row)
        return MockPaymentConfirmResponse(
            order_id=row.id,
            status="paid",
            authorization_id=auth.authorization_id,
        )

    def process_webhook(
        self,
        *,
        provider: str,
        body: bytes,
        signature: str | None,
    ) -> PaymentOrderStatusResponse:
        if not verify_webhook_signature(self._settings.payment_webhook_secret, body, signature):
            raise PaymentServiceError("WEBHOOK_SIGNATURE_INVALID", "Invalid webhook signature", 401)

        payload = PaymentWebhookPayload.model_validate_json(body)
        payload_hash = hashlib.sha256(body).hexdigest()
        existing = self._session.scalars(
            select(PaymentWebhookEventRow).where(
                PaymentWebhookEventRow.provider == provider,
                PaymentWebhookEventRow.provider_ref == payload.provider_ref,
            )
        ).first()
        if existing:
            row = self._orders.get_by_provider_ref(provider, payload.provider_ref)
            if row:
                return self._order_status(row)
            raise PaymentServiceError("ORDER_NOT_FOUND", "Webhook already processed", 404)

        row = self._orders.get(payload.order_id)
        if not row or row.provider != provider:
            raise PaymentServiceError("ORDER_NOT_FOUND", "Payment order not found", 404)
        if row.provider_ref != payload.provider_ref:
            raise PaymentServiceError("PROVIDER_REF_MISMATCH", "provider_ref mismatch", 400)
        if payload.status != "paid":
            raise PaymentServiceError("UNSUPPORTED_STATUS", f"Unsupported status: {payload.status}", 400)

        self._session.add(
            PaymentWebhookEventRow(
                provider=provider,
                provider_ref=payload.provider_ref,
                order_id=row.id,
                payload_hash=payload_hash,
            )
        )
        self._session.commit()

        if row.status == "paid" and row.authorization_id:
            return self._order_status(row)

        self._fulfill_pending_order(row)
        row = self._orders.get(row.id)
        return self._order_status(row)

    def _fulfill_pending_order(self, row):
        if row.status == "paid" and row.authorization_id:
            from voice_platform.job.repository import VoiceAuthorizationRepository

            auth_row = VoiceAuthorizationRepository(self._session).get(row.authorization_id)
            if auth_row:
                entry = self._catalog.get(row.catalog_id)
                title = entry.title if entry else "unknown"
                return self._licensing._auth_response(auth_row, voice_title=title)

        try:
            auth = self._licensing.create_authorization_for_payment(
                catalog_id=row.catalog_id,
                buyer_user_id=row.buyer_user_id,
                payment_ref=row.provider_ref,
            )
        except LicensingServiceError as exc:
            raise PaymentServiceError(exc.code, exc.message, exc.http_status) from exc

        updated = self._orders.mark_paid(row.id, authorization_id=auth.authorization_id)
        if not updated:
            raise PaymentServiceError("ORDER_UPDATE_FAILED", "Failed to mark order paid", 500)
        SettlementService(self._session).credit_from_payment_order(updated)
        return auth
