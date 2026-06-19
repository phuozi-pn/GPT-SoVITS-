from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from domains.voices.service import VoiceServiceError
from voice_platform.job.schemas import VoiceSummary, VoiceVersionSummary

USER = UUID("11111111-1111-1111-1111-111111111111")
VOICE = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VERSION = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "true")
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_list_voices_detail_flag(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.list_voices.return_value = [
            VoiceSummary(voice_id=VOICE, name="demo", version_count=1, latest_version_id=VERSION, versions=[])
        ]
        r = client.get("/api/v1/voices?detail=true")
    assert r.status_code == 200
    svc_cls.return_value.list_voices.assert_called_once()
    assert svc_cls.return_value.list_voices.call_args.kwargs["detail"] is True


def test_update_voice_name(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.update_voice_name.return_value = VoiceSummary(
            voice_id=VOICE, name="新名称", version_count=1, latest_version_id=VERSION
        )
        r = client.patch(f"/api/v1/voices/{VOICE}", json={"name": "新名称"})
    assert r.status_code == 200
    assert r.json()["name"] == "新名称"


def test_delete_version_not_found(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.delete_version.side_effect = VoiceServiceError(
            "VERSION_NOT_FOUND", "音色版本不存在或无权删除", 404
        )
        r = client.delete(f"/api/v1/voice-versions/{VERSION}")
    assert r.status_code == 404


def test_delete_version_in_use(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.delete_version.side_effect = VoiceServiceError(
            "VERSION_IN_USE", "该版本已绑定到批量配音项目角色", 409
        )
        r = client.delete(f"/api/v1/voice-versions/{VERSION}")
    assert r.status_code == 409
    assert r.json()["code"] == "VERSION_IN_USE"


def test_update_version_metadata(client):
    with patch("apps.api.routes.voices.VoiceService") as svc_cls:
        svc_cls.return_value.update_version.return_value = VoiceVersionSummary(
            voice_version_id=VERSION,
            voice_id=VOICE,
            voice_name="demo",
            version=1,
            model_tag="gsv-v2pro",
            label="旁白",
        )
        r = client.patch(f"/api/v1/voice-versions/{VERSION}", json={"label": "旁白"})
    assert r.status_code == 200
    assert r.json()["label"] == "旁白"


def test_unpublish_catalog_owner(client):
    from voice_platform.job.schemas import CatalogEntryResponse

    CATALOG = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.unpublish_catalog_entry.return_value = CatalogEntryResponse(
            catalog_id=CATALOG,
            voice_version_id=VERSION,
            voice_id=VOICE,
            voice_name="demo",
            title="测试音色",
            description="",
            tags=[],
            featured=False,
            status="takedown",
            demo_text="",
            owner_user_id=USER,
            can_use=False,
            license_type="personal_non_commercial",
            price_cents=0,
            billing_unit="per_1k_chars",
            included_chars=50000,
            prohibited_domains=[],
            policy_version=1,
            purchased=False,
        )
        r = client.post(f"/api/v1/catalog/voices/{CATALOG}/unpublish")
    assert r.status_code == 200
    assert r.json()["status"] == "takedown"
