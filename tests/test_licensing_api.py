"""Licensing, purchase, certificate, and complaint API tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

OWNER = UUID("00000000-0000-0000-0000-000000000001")
BUYER = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ADMIN = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CATALOG_ID = UUID("22222222-2222-2222-2222-222222222222")
AUTH_ID = UUID("33333333-3333-3333-3333-333333333333")
COMPLAINT_ID = UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_purchase_api(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        svc_cls.return_value.purchase.return_value = {
            "authorization_id": str(AUTH_ID),
            "catalog_id": str(CATALOG_ID),
            "voice_version_id": str(UUID(int=1)),
            "voice_id": str(UUID(int=2)),
            "voice_title": "测试音色",
            "seller_user_id": str(OWNER),
            "buyer_user_id": str(BUYER),
            "license_type": "commercial_standard",
            "billing_unit": "per_1k_chars",
            "char_quota_total": 50000,
            "char_quota_used": 0,
            "char_quota_remaining": 50000,
            "price_paid_cents": 9900,
            "payment_ref": "mock_pay_abc",
            "status": "active",
        }
        r = client.post(
            f"/api/v1/catalog/voices/{CATALOG_ID}/purchase",
            headers={"X-User-Id": str(BUYER)},
        )
    assert r.status_code == 201
    assert r.json()["payment_ref"].startswith("mock_pay")


def test_authorization_verify_public(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        svc_cls.return_value.verify_certificate.return_value = {
            "authorization_id": str(AUTH_ID),
            "status": "active",
            "valid": True,
            "voice_title": "测试",
            "license_type": "commercial_standard",
            "message": "有效",
        }
        r = client.get(f"/api/v1/authorizations/{AUTH_ID}/verify")
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_submit_complaint(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        svc_cls.return_value.submit_complaint.return_value = {
            "complaint_id": str(COMPLAINT_ID),
            "catalog_id": str(CATALOG_ID),
            "voice_version_id": None,
            "reporter_user_id": str(BUYER),
            "target_url": "",
            "description": "疑似未授权克隆",
            "evidence_urls": [],
            "status": "open",
            "resolution_note": None,
            "created_at": None,
            "resolved_at": None,
        }
        r = client.post(
            "/api/v1/complaints",
            headers={"X-User-Id": str(BUYER)},
            json={"catalog_id": str(CATALOG_ID), "description": "Unauthorized voice clone usage reported"},
        )
    assert r.status_code == 201


def test_admin_complaints_forbidden(client):
    r = client.get("/api/v1/admin/complaints", headers={"X-User-Id": str(BUYER)})
    assert r.status_code == 403


def test_admin_takedown(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        svc_cls.return_value.takedown_complaint.return_value = {
            "complaint_id": str(COMPLAINT_ID),
            "catalog_id": str(CATALOG_ID),
            "voice_version_id": None,
            "reporter_user_id": str(BUYER),
            "target_url": "",
            "description": "侵权",
            "evidence_urls": [],
            "status": "resolved",
            "resolution_note": "Takedown completed",
            "created_at": None,
            "resolved_at": None,
        }
        r = client.post(
            f"/api/v1/admin/complaints/{COMPLAINT_ID}/takedown",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_admin_jobs_owner_filter(client):
    with patch("domains.jobs.service.JobRepository") as repo_cls:
        repo_cls.return_value.list_recent.return_value = []
        r = client.get(
            f"/api/v1/admin/jobs?owner={OWNER}",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    repo_cls.return_value.list_recent.assert_called_once()
    assert repo_cls.return_value.list_recent.call_args.kwargs["owner_user_id"] == OWNER


def test_admin_payments(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        from datetime import datetime, timezone

        svc_cls.return_value.list_payment_orders.return_value = [
            MagicMock(
                order_id=UUID("55555555-5555-5555-5555-555555555555"),
                authorization_id=AUTH_ID,
                catalog_id=CATALOG_ID,
                buyer_user_id=BUYER,
                seller_user_id=OWNER,
                amount_cents=9900,
                currency="CNY",
                status="paid",
                provider="mock",
                provider_ref="mock_pay_abc",
                created_at=datetime.now(timezone.utc),
            )
        ]
        r = client.get("/api/v1/admin/payments", headers={"X-User-Id": str(ADMIN)})
    assert r.status_code == 200
    assert r.json()[0]["provider_ref"] == "mock_pay_abc"
