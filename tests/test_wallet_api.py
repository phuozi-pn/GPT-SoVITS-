from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.config import get_settings
from voice_platform.wallet.schemas import UserWalletResponse, WalletPurchaseResponse

DEV_USER = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_get_wallet(client):
    with patch("domains.wallet.service.UserWalletRepository") as repo_cls:
        wallet = MagicMock()
        wallet.user_id = DEV_USER
        wallet.token_balance = 12000
        wallet.total_purchased_tokens = 50000
        repo_cls.return_value.get_wallet.return_value = wallet
        r = client.get("/api/v1/wallet")
    assert r.status_code == 200
    body = r.json()
    assert body["token_balance"] == 12000
    assert body["total_purchased_tokens"] == 50000


def test_list_packages(client):
    r = client.get("/api/v1/wallet/packages")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 3
    assert body[0]["mock_payment"] is True
    assert body[0]["token_amount"] > 0


def test_purchase_mock(client):
    with patch("domains.wallet.service.WalletService.purchase") as purchase:
        purchase.return_value = WalletPurchaseResponse(
            package_sku="starter",
            tokens_granted=50000,
            token_balance=50000,
            mock_payment=True,
        )
        r = client.post("/api/v1/wallet/purchase", json={"package_sku": "starter"})
    assert r.status_code == 201
    body = r.json()
    assert body["tokens_granted"] == 50000
    assert body["mock_payment"] is True


def test_list_ledger(client):
    with patch("domains.wallet.service.WalletService.list_ledger") as list_ledger:
        list_ledger.return_value = []
        r = client.get("/api/v1/wallet/ledger")
    assert r.status_code == 200
    assert r.json() == []
