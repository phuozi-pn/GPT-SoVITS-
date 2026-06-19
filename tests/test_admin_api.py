"""Admin ops API tests."""
from __future__ import annotations

from uuid import UUID

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

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
