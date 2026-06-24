"""Admin waitlist issue-invite API tests."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

ADMIN = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
WAITLIST_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_list_waitlist(client):
    with patch("apps.api.routes.marketplace.MarketplaceInviteService") as svc_cls:
        svc_cls.return_value.list_waitlist.return_value = [
            {
                "waitlist_id": str(WAITLIST_ID),
                "user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "phone": "13800000000",
                "contact": "wechat:id",
                "note": "creator",
                "created_at": None,
            }
        ]
        r = client.get(
            "/api/v1/admin/marketplace/waitlist",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json()[0]["waitlist_id"] == str(WAITLIST_ID)


def test_admin_issue_waitlist_invite(client):
    with patch("apps.api.routes.marketplace.MarketplaceInviteService") as svc_cls:
        svc_cls.return_value.issue_invite_from_waitlist.return_value = {
            "waitlist_id": str(WAITLIST_ID),
            "user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "code": "PHONIA-AAAAAAAA",
            "message": "issued",
        }
        r = client.post(
            f"/api/v1/admin/marketplace/waitlist/{WAITLIST_ID}/issue-invite",
            headers={"X-User-Id": str(ADMIN)},
            json={},
        )
    assert r.status_code == 200
    assert r.json()["code"] == "PHONIA-AAAAAAAA"
