"""Payment checkout and webhook tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.payment.webhook import sign_webhook_payload

BUYER = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CATALOG_ID = UUID("22222222-2222-2222-2222-222222222222")
ORDER_ID = UUID("55555555-5555-5555-5555-555555555555")
AUTH_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_checkout_api(client):
    with patch("apps.api.routes.payments.PaymentService") as svc_cls:
        svc_cls.return_value.checkout.return_value = MagicMock(
            order_id=ORDER_ID,
            status="pending",
            amount_cents=9900,
            currency="CNY",
            provider="mock",
            provider_ref="chk_abc",
            checkout_url="/api/v1/payments/orders/x/mock-confirm",
            qr_code_url=None,
            authorization_id=None,
        )
        r = client.post(
            f"/api/v1/catalog/voices/{CATALOG_ID}/checkout",
            headers={"X-User-Id": BUYER},
        )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


def test_mock_confirm_api(client):
    with patch("apps.api.routes.payments.PaymentService") as svc_cls:
        svc_cls.return_value.mock_confirm.return_value = MagicMock(
            order_id=ORDER_ID,
            status="paid",
            authorization_id=AUTH_ID,
        )
        r = client.post(
            f"/api/v1/payments/orders/{ORDER_ID}/mock-confirm",
            headers={"X-User-Id": BUYER},
        )
    assert r.status_code == 200
    assert r.json()["authorization_id"] == str(AUTH_ID)


def test_webhook_api(client):
    body = json.dumps(
        {"order_id": str(ORDER_ID), "provider_ref": "chk_abc", "status": "paid"}
    ).encode()
    sig = sign_webhook_payload("dev-payment-webhook-secret-change-me", body)
    with patch("apps.api.routes.payments.PaymentService") as svc_cls:
        svc_cls.return_value.process_webhook.return_value = MagicMock(
            order_id=ORDER_ID,
            status="paid",
            amount_cents=9900,
            provider="mock",
            provider_ref="chk_abc",
            authorization_id=AUTH_ID,
            paid_at=None,
            created_at=None,
        )
        r = client.post(
            "/api/v1/payments/webhooks/mock",
            content=body,
            headers={"X-Payment-Signature": sig, "Content-Type": "application/json"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_purchase_checkout_required_when_async(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        from domains.licensing.service import LicensingServiceError

        svc_cls.return_value.purchase.side_effect = LicensingServiceError(
            "CHECKOUT_REQUIRED",
            "Use checkout",
            409,
        )
        r = client.post(
            f"/api/v1/catalog/voices/{CATALOG_ID}/purchase",
            headers={"X-User-Id": BUYER},
        )
    assert r.status_code == 409
    assert r.json()["code"] == "CHECKOUT_REQUIRED"
