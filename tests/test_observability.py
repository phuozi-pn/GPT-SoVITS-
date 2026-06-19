from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.job.schemas import JOB_SCHEMA_VERSION, JobRecord, JobStatus, JobType
from voice_platform.observability.alerts import maybe_alert_job_failed

JOB_ID = UUID("22222222-2222-2222-2222-222222222222")
USER = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _failed_record() -> JobRecord:
    return JobRecord(
        job_id=JOB_ID,
        job_type=JobType.SYNTHESIZE,
        status=JobStatus.FAILED,
        trace_id="trace-test-001",
        job_schema_version=JOB_SCHEMA_VERSION,
        payload={},
        result=None,
        error_message="Engine set_gpt_weights failed",
        owner_user_id=USER,
        queue_position=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_trace_middleware_returns_header():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health", headers={"X-Trace-Id": "abc-trace-123"})
        assert r.status_code == 200
        assert r.headers.get("X-Trace-Id") == "abc-trace-123"


def test_trace_middleware_generates_header_when_missing():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.headers.get("X-Trace-Id")


def test_alert_skipped_without_webhook():
    with patch("voice_platform.observability.alerts.httpx.Client") as client_cls:
        maybe_alert_job_failed(_failed_record())
        client_cls.assert_not_called()


def test_alert_posts_feishu_payload():
    with patch("voice_platform.observability.alerts.get_settings") as gs:
        settings = MagicMock()
        settings.alert_on_job_failure = True
        settings.alert_webhook_url = "https://example.com/hook"
        settings.alert_webhook_format = "feishu"
        gs.return_value = settings

        with patch("voice_platform.observability.alerts.httpx.Client") as client_cls:
            client = MagicMock()
            client.__enter__.return_value = client
            client.post.return_value.status_code = 200
            client_cls.return_value = client

            maybe_alert_job_failed(_failed_record())

            client.post.assert_called_once()
            args, kwargs = client.post.call_args
            assert args[0] == "https://example.com/hook"
            assert kwargs["json"]["msg_type"] == "text"
            assert "trace-test-001" in kwargs["json"]["content"]["text"]


def test_mark_failed_triggers_alert():
    from voice_platform.job.repository import JobRepository

    row = MagicMock()
    row.id = JOB_ID
    row.job_type = JobType.SYNTHESIZE.value
    row.status = JobStatus.RUNNING.value
    row.trace_id = "trace-repo-1"
    row.job_schema_version = JOB_SCHEMA_VERSION
    row.payload = {}
    row.result = None
    row.error_message = None
    row.owner_user_id = USER
    row.created_at = NOW
    row.updated_at = NOW

    session = MagicMock()
    session.get.return_value = row

    with patch.object(JobRepository, "_queued_position", return_value=None):
        with patch("voice_platform.job.repository.maybe_alert_job_failed") as alert:
            repo = JobRepository(session)
            record = repo.mark_failed(JOB_ID, "boom")
            alert.assert_called_once()
            assert record is not None
            assert record.trace_id == "trace-repo-1"
