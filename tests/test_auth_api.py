from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.config import get_settings
from voice_platform.quota.schemas import QuotaSummary

DEV_USER = "00000000-0000-0000-0000-000000000001"
VOICE = "11111111-1111-1111-1111-111111111101"


@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def client_strict_auth(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "false")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_send_sms_mock(client):
    with patch("domains.auth.service.OtpStore") as otp_cls:
        store = otp_cls.return_value
        store.is_locked.return_value = False
        store.issue.return_value = "654321"
        r = client.post("/api/v1/auth/sms/send", json={"phone": "13800000099"})
    assert r.status_code == 200
    assert r.json()["mock_code"] == "654321"


def test_login_success(client):
    user_id = uuid4()
    quota = QuotaSummary(
        monthly_char_limit=20000,
        chars_used=0,
        chars_remaining=20000,
        monthly_train_limit=1,
        trainings_used=0,
        trainings_remaining=1,
        reset_at=datetime.now(timezone.utc),
    )
    user = MagicMock(id=user_id, phone="13800000099", status="active")
    with (
        patch("domains.auth.service.OtpStore") as otp_cls,
        patch("domains.auth.service.UserRepository") as user_repo_cls,
        patch("domains.auth.service.QuotaRepository") as quota_repo_cls,
    ):
        store = otp_cls.return_value
        store.is_locked.return_value = False
        store.verify.return_value = True
        user_repo_cls.return_value.get_or_create.return_value = user
        quota_repo_cls.return_value.get_summary.return_value = quota
        r = client.post("/api/v1/auth/login", json={"phone": "13800000099", "code": "654321"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["phone"] == "13800000099"


def test_login_invalid_otp(client):
    with patch("domains.auth.service.OtpStore") as otp_cls:
        store = otp_cls.return_value
        store.is_locked.return_value = False
        store.verify.return_value = False
        r = client.post("/api/v1/auth/login", json={"phone": "13800000099", "code": "000000"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_OTP"


def test_login_account_locked(client):
    with patch("domains.auth.service.OtpStore") as otp_cls:
        store = otp_cls.return_value
        store.is_locked.return_value = True
        r = client.post("/api/v1/auth/login", json={"phone": "13800000099", "code": "654321"})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "ACCOUNT_LOCKED"


def test_synthesis_requires_bearer_when_auth_enabled(client_strict_auth):
    r = client_strict_auth.post(
        "/api/v1/synthesis",
        json={"voice_version_id": VOICE, "text": "你好"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_synthesis_with_bearer_token(client_strict_auth):
    from voice_platform.auth.jwt import create_access_token

    token = create_access_token(user_id=UUID(DEV_USER))
    with (
        patch("apps.api.routes.synthesis.VoiceVersionRepository") as repo_cls,
        patch("apps.api.routes.synthesis.QuotaRepository") as quota_cls,
        patch("apps.api.routes.synthesis.SynthesisService") as svc_cls,
    ):
        repo_cls.return_value.user_can_access.return_value = True
        quota_cls.return_value.ensure_chars_available.return_value = None
        from voice_platform.job.schemas import JobStatus, JobSubmitResponse, JobType

        svc_cls.return_value.submit.return_value = JobSubmitResponse(
            job_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            job_type=JobType.SYNTHESIZE,
            status=JobStatus.QUEUED,
            queue_position=1,
        )
        r = client_strict_auth.post(
            "/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": "你好"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 202


def test_invalid_phone_rejected(client):
    r = client.post("/api/v1/auth/sms/send", json={"phone": "12345"})
    assert r.status_code == 422
