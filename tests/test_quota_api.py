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


def _summary(*, chars_used=0, trainings_used=0, chars_remaining=20000, trainings_remaining=1, wallet=0):
    from datetime import datetime, timezone

    return QuotaSummary(
        monthly_char_limit=20000,
        chars_used=chars_used,
        chars_remaining=chars_remaining,
        wallet_token_balance=wallet,
        total_tokens_remaining=chars_remaining + wallet,
        monthly_train_limit=1,
        trainings_used=trainings_used,
        trainings_remaining=trainings_remaining,
        reset_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def test_get_quota(client):
    with patch("domains.quota.service.QuotaRepository") as repo_cls:
        repo_cls.return_value.get_summary.return_value = _summary(chars_used=100)
        r = client.get("/api/v1/usage/quota")
    assert r.status_code == 200
    body = r.json()
    assert body["chars_used"] == 100
    assert body["chars_remaining"] == 20000


def test_synthesis_rejects_quota_exceeded(client):
    with patch("apps.api.routes.synthesis.user_can_access_voice_version") as vv_cls:
        vv_cls.return_value = True
        with patch("apps.api.routes.synthesis.LicensingService") as lic_cls:
            lic_cls.return_value.check_project_domain.return_value = None
            lic_cls.return_value.ensure_purchase_quota.return_value = None
            with patch("domains.quota.service.QuotaRepository") as quota_cls:
                quota_cls.return_value.ensure_chars_available.side_effect = QuotaExceededError(
                    quota_type="chars",
                    message="本月 TTS Token 额度不足，请升级套餐或下月再试",
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
    detail = r.json()
    assert detail["code"] == "QUOTA_EXCEEDED"
    assert detail["details"]["quota_type"] == "chars"
    assert detail["details"]["remaining"] == 50


def test_train_rejects_quota_exceeded(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls, patch(
        "apps.api.routes.voices.TrainingService"
    ) as svc_cls:
        kyc_cls.return_value.ensure_verified_for_train.return_value = None
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (MagicMock(), True, True, True, True)
        with patch("domains.quota.service.QuotaRepository") as quota_cls:
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
    assert r.json()["details"]["quota_type"] == "train"


def test_import_weights_rejects_quota_exceeded(client):
    with patch("domains.quota.service.QuotaRepository") as quota_cls:
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
            "/api/v1/voices/import-weights",
            json={
                "voice_name": "import-test",
                "engine_gpt_weights": "GPT_weights_v2Pro/x.ckpt",
                "engine_sovits_weights": "SoVITS_weights_v2Pro/x.pth",
                "ref_audio_host_path": "/tmp/ref.wav",
                "ref_text": "参考文本",
            },
        )
    assert r.status_code == 402
    assert r.json()["details"]["quota_type"] == "train"


def test_import_weights_records_training_on_success(client):
    from datetime import datetime, timezone

    from voice_platform.job.schemas import VoiceVersionSummary

    version_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    voice_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    summary = _summary(trainings_used=1, trainings_remaining=0)
    imported = VoiceVersionSummary(
        voice_version_id=version_id,
        voice_id=voice_id,
        voice_name="import-test",
        version=1,
        model_tag="gsv-v2pro-20250606",
        label="v1",
        ref_text="参考文本",
        imported=True,
        created_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
    )
    with patch("domains.quota.service.QuotaRepository") as quota_cls, patch(
        "apps.api.routes.voices.EngineWeightsImportService"
    ) as import_cls:
        quota_cls.return_value.ensure_training_available.return_value = None
        quota_cls.return_value.record_training.return_value = True
        quota_cls.return_value.get_summary.return_value = summary
        import_cls.return_value.import_weights.return_value = imported
        r = client.post(
            "/api/v1/voices/import-weights",
            json={
                "voice_name": "import-test",
                "engine_gpt_weights": "GPT_weights_v2Pro/x.ckpt",
                "engine_sovits_weights": "SoVITS_weights_v2Pro/x.pth",
                "ref_audio_host_path": "/tmp/ref.wav",
                "ref_text": "参考文本",
            },
        )
    assert r.status_code == 201
    quota_cls.return_value.record_training.assert_called_once_with(
        user_id=DEV_USER,
        job_id=version_id,
    )


def test_quota_repository_record_idempotent():
    from unittest.mock import patch

    from sqlalchemy.exc import IntegrityError

    from voice_platform.quota.repository import QuotaRepository

    session = MagicMock()
    session.commit.side_effect = [None, IntegrityError("stmt", "params", "orig")]
    repo = QuotaRepository(session)
    with patch.object(repo, "_chars_used", return_value=0), patch.object(
        repo, "_limits_for_user", return_value=(20000, 1)
    ):
        assert repo.record_chars(user_id=DEV_USER, job_id=UUID(int=1), char_count=10) is True
        assert repo.record_chars(user_id=DEV_USER, job_id=UUID(int=1), char_count=10) is False


def test_quota_repository_user_limits_override():
    from voice_platform.auth.models import UserRow
    from voice_platform.quota.repository import QuotaRepository

    user = UserRow(
        id=DEV_USER,
        phone="13800000001",
        quota_monthly_char_limit=None,
        quota_monthly_train_limit=None,
    )
    session = MagicMock()
    session.get.return_value = user
    repo = QuotaRepository(session)
    char_limit, train_limit = repo._limits_for_user(DEV_USER)
    assert char_limit == repo._settings.quota_monthly_char_limit
    assert train_limit == repo._settings.quota_monthly_train_limit

    user.quota_monthly_train_limit = 10
    char_limit, train_limit = repo._limits_for_user(DEV_USER)
    assert train_limit == 10

    repo.set_user_limits(DEV_USER, monthly_char_limit=80000, monthly_train_limit=3)
    assert user.quota_monthly_char_limit == 80000
    assert user.quota_monthly_train_limit == 3
    session.commit.assert_called()
