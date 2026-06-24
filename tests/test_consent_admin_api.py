"""Admin consent review API tests."""
from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

ADMIN = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CONSENT_ID = UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_pending_consents(client):
    with patch("apps.api.routes.consents.ConsentService") as svc_cls:
        svc_cls.return_value.list_pending.return_value = []
        r = client.get(
            "/api/v1/admin/consents/pending",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json() == []


def test_admin_reject_consent(client):
    with patch("apps.api.routes.consents.ConsentService") as svc_cls:
        svc_cls.return_value.reject.return_value = {
            "consent_id": str(CONSENT_ID),
            "voice_id": str(UUID(int=1)),
            "owner_user_id": str(UUID(int=2)),
            "voice_name": "demo",
            "status": "rejected",
            "created_at": None,
            "approved_at": None,
            "reject_reason": "invalid scan",
        }
        r = client.post(
            f"/api/v1/admin/consents/{CONSENT_ID}/reject",
            headers={"X-User-Id": str(ADMIN)},
            json={"reason": "invalid scan"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
