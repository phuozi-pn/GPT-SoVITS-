"""REQ-030 Open API and API key tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.developer.repository import hash_api_key

USER = "00000000-0000-0000-0000-000000000001"
VOICE = "11111111-1111-1111-1111-111111111101"
JOB_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
KEY_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RAW_KEY = "vsk_" + "a" * 32


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_create_api_key(client):
    from voice_platform.developer.schemas import ApiKeyCreatedResponse

    with patch("apps.api.routes.developer.DeveloperService") as svc_cls:
        svc_cls.return_value.create_key.return_value = ApiKeyCreatedResponse(
            key_id=KEY_ID,
            name="ci",
            key_prefix=RAW_KEY[:12],
            api_key=RAW_KEY,
            scopes=["synthesis:write", "jobs:read"],
        )
        r = client.post(
            "/api/v1/developer/api-keys",
            headers={"X-User-Id": USER},
            json={"name": "ci"},
        )
    assert r.status_code == 201
    assert r.json()["api_key"].startswith("vsk_")


def test_open_synthesis_requires_api_key(client):
    r = client.post(
        "/api/v1/open/synthesis",
        json={"voice_version_id": VOICE, "text": "你好"},
    )
    assert r.status_code == 422


def test_open_synthesis_with_key(client):
    with patch("apps.api.routes.open_api.DeveloperService") as dev_cls, patch(
        "apps.api.routes.open_api.user_can_access_voice_version"
    ) as vv_cls, patch("apps.api.routes.open_api.SynthesisService") as svc_cls, patch(
        "domains.quota.service.QuotaRepository"
    ) as quota_cls, patch("apps.api.routes.open_api.LicensingService") as lic_cls:
        key_row = MagicMock(scopes_json=["synthesis:write", "jobs:read"])
        dev_cls.return_value.resolve_user_from_key.return_value = (UUID(USER), key_row)
        dev_cls.return_value.require_scope.return_value = None
        vv_cls.return_value.user_can_access.return_value = True
        quota_cls.return_value.ensure_chars_available.return_value = None
        lic_cls.return_value.check_project_domain.return_value = None
        lic_cls.return_value.ensure_purchase_quota.return_value = None
        from voice_platform.job.schemas import JobStatus, JobSubmitResponse, JobType

        svc_cls.return_value.submit.return_value = JobSubmitResponse(
            job_id=JOB_ID,
            job_type=JobType.SYNTHESIZE,
            status=JobStatus.QUEUED,
            queue_position=1,
        )
        r = client.post(
            "/api/v1/open/synthesis",
            headers={"X-Api-Key": RAW_KEY},
            json={"voice_version_id": VOICE, "text": "你好"},
        )
    assert r.status_code == 202
    assert r.json()["job_id"] == str(JOB_ID)


def test_hash_api_key_deterministic():
    assert hash_api_key("vsk_test") == hash_api_key("vsk_test")
