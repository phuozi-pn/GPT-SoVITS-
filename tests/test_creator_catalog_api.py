"""Creator profile catalog API tests."""
from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

OWNER = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_creator_profile_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.get_creator_profile.return_value = {
            "user_id": str(OWNER),
            "display_name": "138****0001",
            "bio": "",
            "published_count": 1,
            "voices": [],
        }
        r = client.get(f"/api/v1/catalog/creators/{OWNER}")
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "138****0001"
    assert body["published_count"] == 1


def test_catalog_owner_filter_param(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_catalog.return_value = []
        r = client.get(f"/api/v1/catalog/voices?owner={OWNER}")
    assert r.status_code == 200
    svc_cls.return_value.list_catalog.assert_called_once()
    call_kw = svc_cls.return_value.list_catalog.call_args.kwargs
    assert call_kw["owner_user_id"] == OWNER
