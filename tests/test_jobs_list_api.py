from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import pytest
from domains.jobs.service import is_displayable_synthesis_history
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.config import get_settings
from voice_platform.job.schemas import (
    JobRecord,
    JobStatus,
    JobType,
    SynthesisHistoryDetail,
    SynthesisHistoryItem,
)

DEV_USER = UUID("00000000-0000-0000-0000-000000000001")
JOB_ID = UUID("22222222-2222-2222-2222-222222222201")


@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _item() -> SynthesisHistoryItem:
    return SynthesisHistoryItem(
        job_id=JOB_ID,
        status=JobStatus.SUCCEEDED,
        created_at=datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc),
        text_preview="你好世界",
        voice_name="测试音色",
        voice_version_label="v1",
        audio_url="http://localhost/files/out.wav",
        duration_sec=1.2,
        chars_billed=4,
    )


def _detail() -> SynthesisHistoryDetail:
    return SynthesisHistoryDetail(
        **_item().model_dump(),
        full_text="你好世界",
        segments=[],
        updated_at=datetime(2026, 6, 26, 12, 1, tzinfo=timezone.utc),
    )


def test_list_synthesis_jobs(client):
    with patch("domains.jobs.service.JobService.list_synthesis_history") as list_fn:
        list_fn.return_value = [_item()]
        r = client.get("/api/v1/jobs?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["job_id"] == str(JOB_ID)
    assert body[0]["text_preview"] == "你好世界"


def test_get_synthesis_detail(client):
    with patch("domains.jobs.service.JobService.get_synthesis_detail") as detail_fn:
        detail_fn.return_value = _detail()
        r = client.get(f"/api/v1/jobs/{JOB_ID}/detail")
    assert r.status_code == 200
    body = r.json()
    assert body["full_text"] == "你好世界"
    assert body["voice_name"] == "测试音色"


def test_get_synthesis_detail_not_found(client):
    with patch("domains.jobs.service.JobService.get_synthesis_detail") as detail_fn:
        detail_fn.return_value = None
        r = client.get(f"/api/v1/jobs/{JOB_ID}/detail")
    assert r.status_code == 404


def _record(*, status: JobStatus, result: dict | None) -> JobRecord:
    now = datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc)
    return JobRecord(
        job_id=JOB_ID,
        job_type=JobType.SYNTHESIZE,
        status=status,
        trace_id="trace",
        job_schema_version="1.0.0",
        payload={"text": "你好"},
        result=result,
        error_message=None,
        owner_user_id=DEV_USER,
        queue_position=None,
        created_at=now,
        updated_at=now,
    )


def test_is_displayable_synthesis_history():
    assert is_displayable_synthesis_history(
        _record(status=JobStatus.SUCCEEDED, result={"audio_url": "http://localhost/files/a.wav"})
    )
    assert not is_displayable_synthesis_history(_record(status=JobStatus.FAILED, result=None))
    assert not is_displayable_synthesis_history(_record(status=JobStatus.SUCCEEDED, result={}))
    assert not is_displayable_synthesis_history(_record(status=JobStatus.QUEUED, result=None))
