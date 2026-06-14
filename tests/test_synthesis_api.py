from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

VOICE = "11111111-1111-1111-1111-111111111101"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_synthesis_rejects_no_access(client):
    with patch("apps.api.routes.synthesis.VoiceVersionRepository") as repo_cls:
        repo_cls.return_value.user_can_access.return_value = False
        r = client.post(
            "/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": "你好"},
        )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "VOICE_NOT_GRANTED"


def test_synthesis_rejects_sensitive(client):
    with patch("apps.api.routes.synthesis.VoiceVersionRepository") as repo_cls:
        repo_cls.return_value.user_can_access.return_value = True
        r = client.post(
            "/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": "测试敏感词出现"},
        )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "SENSITIVE_WORD"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
