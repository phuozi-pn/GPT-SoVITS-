"""Tests for W3 compliance export and wordlist."""
from __future__ import annotations

import io
import struct
import wave
from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from domains.compliance.export import apply_compliance_label, rhythm_label_wav
from domains.compliance.gateway import ComplianceGateway, ComplianceError
from domains.compliance.wordlist import find_sensitive_word, load_sensitive_words
from voice_platform.job.schemas import JobRecord, JobStatus, JobType

USER = UUID("00000000-0000-0000-0000-000000000001")
JOB = UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime.now(timezone.utc)


def _minimal_wav(duration_sec: float = 0.2, sample_rate: int = 32000) -> bytes:
    buf = io.BytesIO()
    nframes = int(sample_rate * duration_sec)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for _ in range(nframes):
            wf.writeframes(struct.pack("<h", 100))
    return buf.getvalue()


def test_wordlist_loads_default():
    words = load_sensitive_words()
    assert "测试敏感词" in words


def test_find_sensitive_word():
    assert find_sensitive_word("正常文本") is None
    assert find_sensitive_word("这里有测试敏感词") == "测试敏感词"


def test_rhythm_label_wav_duration():
    data = rhythm_label_wav(sample_rate=32000, short_ms=100, long_ms=200)
    with wave.open(io.BytesIO(data), "rb") as wf:
        duration = wf.getnframes() / wf.getframerate()
    assert 0.4 <= duration <= 0.6


def test_apply_compliance_label_prepends_audio():
    body = _minimal_wav(0.2)
    labeled, meta = apply_compliance_label(body, sample_rate=32000)
    assert meta["export_compliant"] is True
    assert meta["label_type"] == "rhythm"
    with wave.open(io.BytesIO(body), "rb") as raw, wave.open(io.BytesIO(labeled), "rb") as out:
        assert out.getnframes() > raw.getnframes()


def test_batch_line_sensitive_isolated():
    gateway = ComplianceGateway()
    with pytest.raises(ComplianceError) as exc:
        gateway.validate_batch_line_text("测试敏感词在这里")
    assert exc.value.code == "SENSITIVE_WORD"
    assert gateway.validate_batch_line_text("正常台词") == "正常台词"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _synth_record(*, export_compliant: bool, audio_url: str) -> JobRecord:
    return JobRecord(
        job_id=JOB,
        job_type=JobType.SYNTHESIZE,
        status=JobStatus.SUCCEEDED,
        trace_id="t",
        job_schema_version="1.0.0",
        payload={},
        result={
            "audio_url": audio_url,
            "export_compliant": export_compliant,
        },
        error_message=None,
        owner_user_id=USER,
        queue_position=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_export_download_requires_compliant_job(client):
    record = _synth_record(
        export_compliant=False,
        audio_url="http://127.0.0.1:8001/files/u/synthesis/x.wav",
    )
    with patch("apps.api.routes.exports.get_job_for_user", return_value=record):
        r = client.get(f"/api/v1/exports/{JOB}/download")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "LABEL_REQUIRED"


def test_export_download_synthesis_ok(client, tmp_path, monkeypatch):
    storage_root = tmp_path / "storage"
    rel = f"{USER}/synthesis/{JOB}.wav"
    wav_path = storage_root / rel
    wav_path.parent.mkdir(parents=True)
    wav_path.write_bytes(_minimal_wav())

    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "http://127.0.0.1:8001/files")
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    record = _synth_record(
        export_compliant=True,
        audio_url=f"http://127.0.0.1:8001/files/{rel}",
    )
    with patch("apps.api.routes.exports.get_job_for_user", return_value=record):
        r = client.get(f"/api/v1/exports/{JOB}/download")
    assert r.status_code == 200
    assert r.headers.get("X-AI-Generated") == "true"
    get_settings.cache_clear()
