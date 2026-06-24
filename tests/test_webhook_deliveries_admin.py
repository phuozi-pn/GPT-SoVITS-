"""Admin webhook delivery list API tests."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

ADMIN = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_list_webhook_deliveries(client):
    delivery_id = uuid4()
    with patch("apps.api.routes.developer.WebhookDeliveryRepository") as repo_cls:
        row = type("Row", (), {
            "id": delivery_id,
            "channel": "open_api_job",
            "target_url": "https://example.com/hook",
            "status": "delivered",
            "attempts": 1,
            "max_attempts": 5,
            "last_status_code": 200,
            "last_error": None,
            "delivered_at": None,
            "created_at": None,
        })()
        repo_cls.return_value.list_recent.return_value = [row]
        r = client.get(
            "/api/v1/admin/webhook-deliveries",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json()[0]["delivery_id"] == str(delivery_id)
    assert r.json()[0]["status"] == "delivered"
