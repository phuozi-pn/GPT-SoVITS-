from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.config import get_settings
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.schemas import QuotaSummary

DEV_USER = UUID("00000000-0000-0000-0000-000000000001")
VOICE = "11111111-1111-1111-1111-111111111101"
VOICE_PROFILE = "11111111-1111-1111-1111-111111111100"


@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _summary(*, chars_used=0, trainings_used=0, chars_remaining=20000, trainings_remaining=1):
    from datetime import datetime, timezone

    return QuotaSummary(
        monthly_char_limit=20000,
        chars_used=chars_used,
        chars_remaining=chars_remaining,
        monthly_train_limit=1,
        trainings_used=trainings_used,
        trainings_remaining=trainings_remaining,
        reset_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def test_get_quota(client):
    with patch("apps.api.routes.usage.QuotaRepository") as repo_cls:
        repo_cls.return_value.get_summary.return_value = _summary(chars_used=100)
        r = client.get("/api/v1/usage/quota")
    assert r.status_code == 200
    body = r.json()
    assert body["chars_used"] == 100
    assert body["chars_remaining"] == 20000


def test_synthesis_rejects_quota_exceeded(client):
    with patch("apps.api.routes.synthesis.VoiceVersionRepository") as vv_cls:
        vv_cls.return_value.user_can_access.return_value = True
        with patch("apps.api.routes.synthesis.QuotaRepository") as quota_cls:
            quota_cls.return_value.ensure_chars_available.side_effect = QuotaExceededError(
                quota_type="chars",
                message="本月合成字符额度不足，请升级套餐或下月再试",
                required=100,
                remaining=50,
                monthly_limit=20000,
                used=19950,
                reset_at=_summary().reset_at,
            )
            r = client.post(
                "/api/v1/synthesis",
                json={"voice_version_id": VOICE, "text": "你好世界" * 20},
            )
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "QUOTA_EXCEEDED"
    assert detail["details"]["quota_type"] == "chars"
    assert detail["details"]["remaining"] == 50


def test_train_rejects_quota_exceeded(client):
    with patch("apps.api.routes.voices.TrainingService") as svc_cls:
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (MagicMock(), True, True, True, True)
        with patch("apps.api.routes.voices.QuotaRepository") as quota_cls:
            quota_cls.return_value.ensure_training_available.side_effect = QuotaExceededError(
                quota_type="train",
                message="本月训练次数已达上限，请升级套餐或下月再试",
                required=1,
                remaining=0,
                monthly_limit=1,
                used=1,
                reset_at=_summary(trainings_remaining=0).reset_at,
            )
            r = client.post(
                f"/api/v1/voices/{VOICE_PROFILE}/train",
                json={"model_tag": "gsv-v2pro-20250606"},
            )
    assert r.status_code == 402
    assert r.json()["detail"]["details"]["quota_type"] == "train"


def test_quota_repository_record_idempotent():
    from sqlalchemy.exc import IntegrityError

    from voice_platform.quota.repository import QuotaRepository

    session = MagicMock()
    session.commit.side_effect = [None, IntegrityError("stmt", "params", "orig")]
    repo = QuotaRepository(session)
    assert repo.record_chars(user_id=DEV_USER, job_id=UUID(int=1), char_count=10) is True
    assert repo.record_chars(user_id=DEV_USER, job_id=UUID(int=1), char_count=10) is False
