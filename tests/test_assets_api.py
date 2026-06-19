from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.job.schemas import AssetUploadResponse, QcIssue, QcResult

VOICE = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_upload_rejects_without_consent(client):
    with patch("apps.api.routes.assets.AssetService") as svc_cls:
        from domains.assets.qc import AssetQcError

        svc_cls.return_value.upload.side_effect = AssetQcError(
            "CONSENT_REQUIRED", "Approved consent required"
        )
        r = client.post(
            "/api/v1/voices/assets",
            data={"voice_id": str(VOICE)},
            files={"audio_file": ("a.wav", b"RIFF", "audio/wav")},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "CONSENT_REQUIRED"


def test_upload_returns_qc_report(client):
    qc = QcResult(
        status="passed",
        duration_sec=540.0,
        sample_rate=32000,
        channels=1,
        issues=[],
    )
    body = AssetUploadResponse(
        asset_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        voice_id=VOICE,
        storage_uri="local://user/training/b.wav",
        qc_passed=True,
        qc_result=qc,
    )
    with patch("apps.api.routes.assets.AssetService") as svc_cls:
        svc_cls.return_value.upload.return_value = body
        r = client.post(
            "/api/v1/voices/assets",
            data={"voice_id": str(VOICE), "ref_text": "测试文本"},
            files={"audio_file": ("a.wav", b"RIFF", "audio/wav")},
        )
    assert r.status_code == 201
    assert r.json()["qc_passed"] is True


def test_confirm_rejects_qc_not_passed(client):
    with patch("apps.api.routes.assets.AssetService") as svc_cls:
        from domains.assets.qc import AssetQcError

        svc_cls.return_value.confirm.side_effect = AssetQcError(
            "QC_NOT_PASSED", "QC must pass"
        )
        r = client.post("/api/v1/voices/assets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/confirm")
    assert r.status_code == 422
    assert r.json()["code"] == "QC_NOT_PASSED"


def test_create_voice(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        from voice_platform.job.schemas import VoiceCreateResponse

        svc_cls.return_value.create.return_value = VoiceCreateResponse(
            voice_id=VOICE,
            name="我的音色",
        )
        r = client.post("/api/v1/voices", json={"name": "我的音色"})
    assert r.status_code == 201
    assert r.json()["name"] == "我的音色"
