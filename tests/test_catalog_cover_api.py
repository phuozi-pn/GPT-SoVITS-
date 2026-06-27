"""Catalog cover generation API tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.job.schemas import CatalogCoverGenerateResponse, CatalogEntryResponse

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_generate_cover_preview_ok(client: TestClient):
    fake = CatalogCoverGenerateResponse(
        cover_image_url="http://storage.test/00000000-0000-0000-0000-000000000001/catalog/covers/x.png",
        prompt="test prompt",
    )
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.generate_catalog_cover_preview.return_value = fake
        r = client.post(
            "/api/v1/catalog/voices/generate-cover",
            headers={"X-User-Id": USER},
            json={"title": "测试音色", "tags": ["男声", "男主", "沉稳"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["cover_image_url"].endswith(".png")
    assert body["prompt"] == "test prompt"


def test_generate_cover_preview_disabled(client: TestClient):
    from domains.marketplace.service import MarketplaceServiceError

    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.generate_catalog_cover_preview.side_effect = MarketplaceServiceError(
            "COVER_GEN_DISABLED",
            "封面 AI 生成未启用",
            503,
        )
        r = client.post(
            "/api/v1/catalog/voices/generate-cover",
            headers={"X-User-Id": USER},
            json={"title": "测试音色", "tags": ["男声"]},
        )
    assert r.status_code == 503
    detail = r.json().get("detail", r.json())
    assert detail["code"] == "COVER_GEN_DISABLED"


def test_generate_cover_for_entry_ok(client: TestClient):
    catalog_id = "22222222-2222-2222-2222-222222222222"
    fake_entry = CatalogEntryResponse(
        catalog_id=UUID(catalog_id),
        voice_version_id=UUID("33333333-3333-3333-3333-333333333333"),
        voice_id=UUID("44444444-4444-4444-4444-444444444444"),
        voice_name="demo",
        title="测试音色",
        description="",
        tags=["男声"],
        featured=False,
        status="published",
        cover_image_url="http://storage.test/cover.png",
        owner_user_id=UUID(USER),
    )
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        svc_cls.return_value.generate_catalog_cover_for_entry.return_value = fake_entry
        r = client.post(
            f"/api/v1/catalog/voices/{catalog_id}/generate-cover",
            headers={"X-User-Id": USER},
        )
    assert r.status_code == 200
    assert r.json()["cover_image_url"] == "http://storage.test/cover.png"


def test_generate_and_store_catalog_cover_integration():
    from domains.marketplace.cover_image import generate_and_store_catalog_cover

    owner = UUID(USER)
    with (
        patch("domains.marketplace.cover_image.get_settings") as settings_cls,
        patch("domains.marketplace.cover_image.WanxClient") as wanx_cls,
        patch("domains.marketplace.cover_image.LocalStorage") as storage_cls,
    ):
        settings = MagicMock()
        settings.catalog_cover_gen_enabled = True
        settings_cls.return_value = settings
        wanx_cls.return_value.enabled = True
        wanx_cls.return_value.generate_png.return_value = b"png-bytes"
        storage_cls.return_value.save_bytes.return_value = f"{USER}/catalog/covers/x.png"
        storage_cls.return_value.public_url.return_value = "http://storage.test/cover.png"

        url, prompt = generate_and_store_catalog_cover(
            owner_user_id=owner,
            title="龙渊",
            tags=["男声", "男主", "沉稳"],
        )

    assert url == "http://storage.test/cover.png"
    assert "龙渊" in prompt
    wanx_cls.return_value.generate_png.assert_called_once()
