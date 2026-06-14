"""Tests for MVP+1 catalog and VoiceGrant access."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from domains.voices.access import user_can_access_voice_version

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
