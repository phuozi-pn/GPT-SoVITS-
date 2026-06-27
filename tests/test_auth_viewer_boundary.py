"""Ensure anonymous viewer cannot mutate state."""
from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.config import get_settings

AUTH_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def strict_client(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "false")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_viewer_cannot_create_community_post(strict_client):
    r = strict_client.post(
        "/api/v1/community/posts",
        json={"body": "hello from anonymous", "tags": []},
    )
    assert r.status_code == 401


def test_viewer_cannot_send_message(strict_client):
    r = strict_client.post(
        "/api/v1/messages",
        json={
            "recipient_user_id": "00000000-0000-0000-0000-000000000002",
            "body": "hi",
        },
    )
    assert r.status_code == 401


def test_viewer_invalid_bearer_can_read_public_catalog(strict_client, monkeypatch):
    from domains import marketplace as marketplace_mod

    monkeypatch.setattr(
        marketplace_mod.service.MarketplaceService,
        "list_catalog",
        lambda self, **kwargs: [],
    )

    r = strict_client.get(
        "/api/v1/public/catalog",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert r.status_code == 200


def test_viewer_can_read_public_feed(strict_client, monkeypatch):
    from domains import community as community_mod
    from voice_platform.community.schemas import FeedResponse

    monkeypatch.setattr(
        community_mod.service.CommunityService,
        "feed",
        lambda self, *, viewer_user_id, before, limit=30: FeedResponse(items=[], next_before=None),
    )

    r = strict_client.get("/api/v1/community/feed")
    assert r.status_code == 200


def test_viewer_can_verify_authorization(strict_client, monkeypatch):
    from domains import licensing as licensing_mod
    from voice_platform.job.schemas import AuthorizationVerifyResponse

    monkeypatch.setattr(
        licensing_mod.service.LicensingService,
        "verify_certificate",
        lambda self, authorization_id: AuthorizationVerifyResponse(
            authorization_id=authorization_id,
            status="active",
            valid=True,
            voice_title="Demo",
            license_type="commercial_standard",
            message="ok",
        ),
    )

    r = strict_client.get(f"/api/v1/authorizations/{AUTH_ID}/verify")
    assert r.status_code == 200
    assert r.json()["valid"] is True
