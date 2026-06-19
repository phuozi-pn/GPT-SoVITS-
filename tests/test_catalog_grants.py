"""Tests for MVP+1 catalog and VoiceGrant access."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from domains.voices.access import user_can_access_voice_version

ADMIN = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER = UUID("00000000-0000-0000-0000-000000000001")
OTHER = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VOICE_ID = UUID("11111111-1111-1111-1111-111111111100")
VERSION_ID = UUID("11111111-1111-1111-1111-111111111101")


def _version(owner=OWNER):
    return MagicMock(voice_id=VOICE_ID, owner_user_id=owner, id=VERSION_ID)


def test_access_owner():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = False
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = False
                assert user_can_access_voice_version(session, VERSION_ID, OWNER) is True


def test_access_catalog_public():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = True
            assert user_can_access_voice_version(session, VERSION_ID, OTHER) is True


def test_access_grant():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = False
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = True
                assert user_can_access_voice_version(session, VERSION_ID, OTHER) is True


def test_access_denied():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = False
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = False
                assert user_can_access_voice_version(session, VERSION_ID, OTHER) is False


@pytest.fixture
def client():
    from apps.api.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_catalog_list_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_catalog.return_value = []
        r = client.get("/api/v1/catalog/voices")
    assert r.status_code == 200
    assert r.json() == []


def test_catalog_list_with_tags(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_catalog.return_value = []
        r = client.get("/api/v1/catalog/voices?tags=短剧,男声")
    assert r.status_code == 200
    svc_cls.return_value.list_catalog.assert_called_once()
    kwargs = svc_cls.return_value.list_catalog.call_args.kwargs
    assert kwargs["tags"] == ["短剧", "男声"]


def test_catalog_tags_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_catalog_tags.return_value = ["短剧", "男声"]
        r = client.get("/api/v1/catalog/tags")
    assert r.status_code == 200
    assert r.json() == ["短剧", "男声"]


def test_grants_issued_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_grants_issued.return_value = []
        r = client.get("/api/v1/voice-grants/issued")
    assert r.status_code == 200
    assert r.json() == []


def test_catalog_pending_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.list_pending_review.return_value = []
        r = client.get(
            "/api/v1/catalog/voices/pending",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json() == []


def test_catalog_approve_api(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        from voice_platform.job.schemas import CatalogEntryResponse

        svc_cls.return_value.approve_catalog_entry.return_value = CatalogEntryResponse(
            catalog_id=UUID("22222222-2222-2222-2222-222222222222"),
            voice_version_id=VERSION_ID,
            voice_id=VOICE_ID,
            voice_name="demo",
            title="demo",
            description="",
            featured=True,
            status="published",
            demo_text="试听",
            owner_user_id=OWNER,
        )
        r = client.post(
            f"/api/v1/catalog/voices/{UUID('22222222-2222-2222-2222-222222222222')}/approve",
            headers={"X-User-Id": str(ADMIN)},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "published"


def test_list_versions_includes_granted(client):
    from voice_platform.job.schemas import VoiceVersionSummary

    granted = VoiceVersionSummary(
        voice_version_id=VERSION_ID,
        voice_id=VOICE_ID,
        voice_name="shared",
        version=1,
        model_tag="test",
        granted=True,
    )
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.list_versions.return_value = [granted]
        r = client.get("/api/v1/voice-versions")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["granted"] is True
