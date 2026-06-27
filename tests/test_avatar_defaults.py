from __future__ import annotations

from uuid import UUID

from domains.marketplace.avatar_defaults import (
    default_catalog_cover_url,
    default_creator_avatar_url,
    resolve_catalog_cover_url,
    resolve_creator_avatar_url,
)


def test_default_catalog_cover_by_gender():
    assert default_catalog_cover_url(["女声", "女主"]) == "/catalog/covers/voice-female-01.svg"
    assert default_catalog_cover_url(["童声", "萌娃"]) == "/catalog/covers/voice-female-01.svg"
    assert default_catalog_cover_url(["男声", "男主"]) == "/catalog/covers/voice-male-01.svg"
    assert default_catalog_cover_url(["男主", "反派"]) == "/catalog/covers/voice-male-01.svg"


def test_resolve_catalog_cover_prefers_custom():
    custom = "https://cdn.example.com/cover.png"
    assert resolve_catalog_cover_url(tags=["男声"], cover_image_url=custom) == custom
    assert (
        resolve_catalog_cover_url(tags=["男声"], cover_image_url=None)
        == "/catalog/covers/voice-male-01.svg"
    )


def test_default_creator_avatar_stable():
    uid = UUID("00000000-0000-0000-0000-000000000001")
    first = default_creator_avatar_url(user_id=uid)
    second = default_creator_avatar_url(user_id=uid)
    assert first == second
    assert first in {"/catalog/covers/voice-male-01.svg", "/catalog/covers/voice-female-01.svg"}


def test_resolve_creator_avatar_prefers_custom():
    custom = "/files/u1/avatar.png"
    uid = UUID("00000000-0000-0000-0000-000000000002")
    assert resolve_creator_avatar_url(user_id=uid, avatar_url=custom) == custom
    assert resolve_creator_avatar_url(user_id=uid, avatar_url=None) == default_creator_avatar_url(
        user_id=uid
    )


def test_relink_stored_covers(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from domains.marketplace.avatar_assign import AvatarAssignService
    from voice_platform.config import get_settings

    owner = UUID("00000000-0000-0000-0000-000000000001")
    catalog_id = UUID("22222222-2222-2222-2222-222222222222")
    cover_dir = tmp_path / str(owner) / "catalog" / "covers"
    cover_dir.mkdir(parents=True)
    (cover_dir / f"{catalog_id}.png").write_bytes(b"png")

    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()

    entry = SimpleNamespace(
        id=catalog_id,
        owner_user_id=owner,
        cover_image_url="/catalog/covers/voice-male-01.svg",
    )
    session = MagicMock()
    session.scalars.return_value.all.return_value = [entry]
    svc = AvatarAssignService(session)
    svc._catalog = MagicMock()

    relinked = svc.relink_stored_covers()

    assert relinked == 1
    expected = f"/files/{owner}/catalog/covers/{catalog_id}.png"
    svc._catalog.set_cover_image_url.assert_called_once_with(catalog_id, cover_image_url=expected)
    get_settings.cache_clear()
