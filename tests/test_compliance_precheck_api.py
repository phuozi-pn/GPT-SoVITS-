"""Compliance precheck API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_compliance_precheck_ok(client: TestClient):
    r = client.post(
        "/api/v1/compliance/precheck",
        headers={"X-User-Id": USER},
        json={"texts": ["你好，欢迎试听。"], "segmented": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["issues"] == []
    assert body["total_chars"] == 8


def test_compliance_precheck_sensitive(client: TestClient):
    r = client.post(
        "/api/v1/compliance/precheck",
        headers={"X-User-Id": USER},
        json={"texts": ["这里有测试敏感词"], "segmented": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["issues"][0]["code"] == "SENSITIVE_WORD"
