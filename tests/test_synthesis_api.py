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
    with patch("apps.api.routes.synthesis.user_can_access_voice_version") as repo_cls:
        repo_cls.return_value = False
        r = client.post(
            "/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": "你好"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "VOICE_NOT_GRANTED"


def test_synthesis_rejects_sensitive(client):
    with patch("apps.api.routes.synthesis.user_can_access_voice_version") as repo_cls:
        repo_cls.return_value = True
        r = client.post(
            "/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": "测试敏感词出现"},
        )
    assert r.status_code == 400
    assert r.json()["code"] == "SENSITIVE_WORD"


def test_synthesis_rejects_no_ai_disclosure(client):
    with patch("apps.api.routes.synthesis.user_can_access_voice_version") as repo_cls:
        repo_cls.return_value = True
        r = client.post(
            "/api/v1/synthesis",
            json={
                "voice_version_id": VOICE,
                "text": "你好",
                "ai_disclosure_ack": False,
            },
        )
    assert r.status_code == 403
    assert r.json()["code"] == "AI_DISCLOSURE_REQUIRED"


def test_synthesis_accepts_tune_params(client):
    with patch("apps.api.routes.synthesis.user_can_access_voice_version") as repo_cls, patch(
        "apps.api.routes.synthesis.SynthesisService"
    ) as svc_cls, patch("domains.quota.service.QuotaRepository") as quota_cls, patch(
        "apps.api.routes.synthesis.LicensingService"
    ) as lic_cls:
        repo_cls.return_value.user_can_access.return_value = True
        quota_cls.return_value.ensure_chars_available.return_value = None
        lic_cls.return_value.check_project_domain.return_value = None
        lic_cls.return_value.ensure_purchase_quota.return_value = None
        svc_cls.return_value.submit.return_value = MagicMock(
            job_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            status="queued",
            queue_position=1,
        )
        r = client.post(
            "/api/v1/synthesis",
            json={
                "voice_version_id": VOICE,
                "text": "你好",
                "speed_factor": 1.1,
                "temperature": 0.8,
            },
        )
    assert r.status_code == 202


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "release" in body
