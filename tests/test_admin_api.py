"""Admin ops API tests."""
from __future__ import annotations

from uuid import UUID

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.quota.schemas import UserUsageReportRow

ADMIN = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_jobs_forbidden_for_normal_user(client: TestClient):
    r = client.get(
        "/api/v1/admin/jobs",
        headers={"X-User-Id": USER},
    )
    assert r.status_code == 403


def test_admin_jobs_ok_for_admin(client: TestClient):
    with patch("domains.jobs.service.JobRepository") as repo_cls:
        repo_cls.return_value.list_recent.return_value = []
        r = client.get(
            "/api/v1/admin/jobs",
            headers={"X-User-Id": ADMIN},
            params={"limit": 5},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_admin_stats_ok(client: TestClient):
    with patch("domains.jobs.service.JobRepository") as repo_cls:
        repo_cls.return_value.count_by_status.return_value = 0
        repo_cls.return_value.count_failed_since.return_value = 0
        r = client.get(
            "/api/v1/admin/stats",
            headers={"X-User-Id": ADMIN},
        )
    assert r.status_code == 200
    body = r.json()
    assert "release" in body
    assert "jobs_failed_24h" in body


def test_admin_usage_report_ok(client: TestClient):
    with patch("apps.api.routes.admin.QuotaService") as svc_cls:
        svc_cls.return_value.list_usage_report.return_value = [
            UserUsageReportRow(
                user_id=USER,
                phone="138****0001",
                chars_used=1200,
                trainings_used=2,
                monthly_char_limit=20000,
                monthly_train_limit=1,
                chars_remaining=18800,
                trainings_remaining=0,
            )
        ]
        r = client.get(
            "/api/v1/admin/usage-report",
            headers={"X-User-Id": ADMIN},
            params={"limit": 10},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["chars_used"] == 1200
    assert body["items"][0]["monthly_train_limit"] == 1


def test_admin_set_user_quota_ok(client: TestClient):
    from datetime import datetime, timezone

    from voice_platform.quota.schemas import QuotaSummary

    summary = QuotaSummary(
        monthly_char_limit=50000,
        chars_used=1200,
        chars_remaining=48800,
        monthly_train_limit=5,
        trainings_used=2,
        trainings_remaining=3,
        reset_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    with patch("apps.api.routes.admin.QuotaService") as svc_cls:
        svc_cls.return_value.set_user_limits.return_value = summary
        r = client.patch(
            f"/api/v1/admin/users/{USER}/quota",
            headers={"X-User-Id": ADMIN},
            json={"monthly_char_limit": 50000, "monthly_train_limit": 5},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["monthly_char_limit"] == 50000
    assert body["monthly_train_limit"] == 5
    svc_cls.return_value.set_user_limits.assert_called_once()


def test_admin_set_user_quota_forbidden(client: TestClient):
    r = client.patch(
        f"/api/v1/admin/users/{USER}/quota",
        headers={"X-User-Id": USER},
        json={"monthly_train_limit": 3},
    )
    assert r.status_code == 403
