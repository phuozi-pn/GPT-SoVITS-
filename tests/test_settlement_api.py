"""REQ-028 settlement API tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

OWNER = "00000000-0000-0000-0000-000000000001"
ADMIN = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PAYOUT_ID = UUID("66666666-6666-6666-6666-666666666666")


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_seller_wallet_api(client):
    with patch("apps.api.routes.settlement.SettlementService") as svc_cls:
        svc_cls.return_value.get_wallet.return_value = MagicMock(
            seller_user_id=UUID(OWNER),
            balance_cents=8415,
            pending_payout_cents=0,
            total_earned_cents=8415,
            platform_fee_bps=1500,
            min_payout_cents=10000,
        )
        r = client.get("/api/v1/seller/wallet", headers={"X-User-Id": OWNER})
    assert r.status_code == 200
    assert r.json()["balance_cents"] == 8415


def test_request_payout_api(client):
    with patch("apps.api.routes.settlement.SettlementService") as svc_cls:
        svc_cls.return_value.request_payout.return_value = MagicMock(
            payout_id=PAYOUT_ID,
            seller_user_id=UUID(OWNER),
            amount_cents=10000,
            status="pending",
            note=None,
            created_at=None,
            processed_at=None,
        )
        r = client.post(
            "/api/v1/seller/payouts",
            headers={"X-User-Id": OWNER},
            json={"amount_cents": 10000},
        )
    assert r.status_code == 201


def test_admin_approve_payout(client):
    with patch("apps.api.routes.settlement.SettlementService") as svc_cls:
        svc_cls.return_value.approve_payout.return_value = MagicMock(
            payout_id=PAYOUT_ID,
            seller_user_id=UUID(OWNER),
            amount_cents=10000,
            status="paid",
            note="ok",
            created_at=None,
            processed_at=None,
        )
        r = client.post(
            f"/api/v1/admin/payouts/{PAYOUT_ID}/approve",
            headers={"X-User-Id": ADMIN},
            json={"note": "mock transfer"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_credit_fee_calculation():
    from voice_platform.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    gross = 9900
    fee = round(gross * settings.settlement_platform_fee_bps / 10000)
    assert fee == 1485
    assert gross - fee == 8415
