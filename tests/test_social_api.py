from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

USER_A = UUID("00000000-0000-0000-0000-000000000001")
USER_B = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "true")
    monkeypatch.setenv("DEV_USER_ID", str(USER_A))
    return TestClient(create_app())


def test_user_directory_and_profile(client, monkeypatch):
    from domains.social import service as social_mod

    monkeypatch.setattr(
        social_mod.SocialService,
        "list_directory",
        lambda self, viewer_user_id, limit=50: [],
    )
    from voice_platform.social.schemas import UserPublicProfileResponse

    monkeypatch.setattr(
        social_mod.SocialService,
        "get_profile",
        lambda self, user_id, viewer_user_id: UserPublicProfileResponse(
            user_id=user_id,
            display_name="测试用户",
            bio="hello",
            published_voice_count=1,
            is_self=user_id == viewer_user_id,
        ),
    )
    r = client.get("/api/v1/users/directory", headers={"X-User-Id": str(USER_A)})
    assert r.status_code == 200
    r2 = client.get(f"/api/v1/users/{USER_B}", headers={"X-User-Id": str(USER_A)})
    assert r2.status_code == 200
    assert r2.json()["display_name"] == "测试用户"


def test_send_and_list_messages(client, monkeypatch):
    from domains.social import service as social_mod
    from voice_platform.social.schemas import MessageResponse

    now = datetime.now(timezone.utc)
    msg = MessageResponse(
        message_id=uuid4(),
        sender_user_id=USER_B,
        recipient_user_id=USER_A,
        body="你好",
        read_at=None,
        created_at=now,
    )

    monkeypatch.setattr(
        social_mod.SocialService,
        "send_message",
        lambda self, sender_user_id, body: msg,
    )
    monkeypatch.setattr(
        social_mod.SocialService,
        "list_thread",
        lambda self, user_id, peer_user_id: [msg],
    )

    sent = client.post(
        "/api/v1/messages",
        headers={"X-User-Id": str(USER_B)},
        json={"recipient_user_id": str(USER_A), "body": "你好"},
    )
    assert sent.status_code == 201
    thread = client.get(f"/api/v1/messages/with/{USER_B}", headers={"X-User-Id": str(USER_A)})
    assert thread.status_code == 200
    assert thread.json()[0]["body"] == "你好"
