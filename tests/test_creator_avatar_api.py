"""Creator avatar generation API tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from voice_platform.social.schemas import AvatarGenerateResponse

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_generate_creator_avatar_ok(client: TestClient):
    fake = AvatarGenerateResponse(
        avatar_url="http://storage.test/00000000-0000-0000-0000-000000000001/users/avatars/x.png",
        prompt="test prompt",
    )
    with patch("apps.api.routes.social.SocialService") as svc_cls:
        svc_cls.return_value.generate_my_avatar.return_value = fake
        r = client.post(
            "/api/v1/users/me/profile/generate-avatar",
            headers={"X-User-Id": USER},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["avatar_url"].endswith(".png")
    assert body["prompt"] == "test prompt"


def test_generate_and_store_creator_avatar_integration():
    from domains.marketplace.cover_image import generate_and_store_creator_avatar

    user_id = UUID(USER)
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
        storage_cls.return_value.save_bytes.return_value = f"{USER}/users/avatars/{USER}.png"
        storage_cls.return_value.public_url.return_value = "http://storage.test/avatar.png"

        url, prompt = generate_and_store_creator_avatar(
            user_id=user_id,
            display_name="配音练习生",
            bio="热爱声音创作",
        )

    assert url == "http://storage.test/avatar.png"
    assert "配音练习生" in prompt
    wanx_cls.return_value.generate_png.assert_called_once()
