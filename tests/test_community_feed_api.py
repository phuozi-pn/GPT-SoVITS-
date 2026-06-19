from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_community_feed_smoke(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "true")

    from domains import community as community_mod
    from voice_platform.community.schemas import FeedResponse

    monkeypatch.setattr(
        community_mod.service.CommunityService,
        "feed",
        lambda self, viewer_user_id, before, limit=30: FeedResponse(items=[], next_before=None),
    )

    client = TestClient(create_app())
    r = client.get("/api/v1/community/feed", headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_community_feed_anonymous(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "false")

    from domains import community as community_mod
    from voice_platform.community.schemas import FeedResponse

    seen: list = []

    def fake_feed(self, *, viewer_user_id, before, limit=30):
        seen.append(viewer_user_id)
        return FeedResponse(items=[], next_before=None)

    monkeypatch.setattr(community_mod.service.CommunityService, "feed", fake_feed)

    client = TestClient(create_app())
    r = client.get("/api/v1/community/feed")
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert len(seen) == 1

