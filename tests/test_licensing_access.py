"""Access control for paid catalog purchases."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

from domains.voices.access import user_can_access_voice_version

OWNER = UUID("00000000-0000-0000-0000-000000000001")
BUYER = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VOICE_ID = UUID("11111111-1111-1111-1111-111111111100")
VERSION_ID = UUID("11111111-1111-1111-1111-111111111101")
CATALOG_ID = UUID("22222222-2222-2222-2222-222222222222")


def _version(owner=OWNER):
    return MagicMock(voice_id=VOICE_ID, owner_user_id=owner, id=VERSION_ID)


def _published_entry(*, price_cents=0):
    return MagicMock(
        id=CATALOG_ID,
        voice_version_id=VERSION_ID,
        owner_user_id=OWNER,
        status="published",
        price_cents=price_cents,
    )


def test_access_free_public_catalog():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = True
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = False
                with patch("domains.voices.access.VoiceAuthorizationRepository") as a_cls:
                    a_cls.return_value.has_active_for_voice.return_value = False
                    assert user_can_access_voice_version(session, VERSION_ID, BUYER) is True


def test_access_paid_catalog_requires_purchase():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = False
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = False
                with patch("domains.voices.access.VoiceAuthorizationRepository") as a_cls:
                    a_cls.return_value.has_active_for_voice.return_value = False
                    assert user_can_access_voice_version(session, VERSION_ID, BUYER) is False


def test_access_paid_catalog_with_authorization():
    session = MagicMock()
    with patch("domains.voices.access.VoiceVersionRepository") as v_cls:
        v_cls.return_value.get.return_value = _version(OWNER)
        with patch("domains.voices.access.VoiceCatalogRepository") as c_cls:
            c_cls.return_value.is_publicly_listed.return_value = False
            with patch("domains.voices.access.VoiceGrantRepository") as g_cls:
                g_cls.return_value.has_active_grant.return_value = False
                with patch("domains.voices.access.VoiceAuthorizationRepository") as a_cls:
                    a_cls.return_value.has_active_for_voice.return_value = True
                    assert user_can_access_voice_version(session, VERSION_ID, BUYER) is True


def test_is_publicly_listed_only_free():
    from voice_platform.job.repository import VoiceCatalogRepository

    session = MagicMock()
    repo = VoiceCatalogRepository(session)
    free = _published_entry(price_cents=0)
    paid = _published_entry(price_cents=9900)

    with patch.object(repo, "get_by_version", side_effect=lambda vid: free if vid == VERSION_ID else paid):
        assert repo.is_publicly_listed(VERSION_ID) is True
        other = UUID("99999999-9999-9999-9999-999999999999")
        assert repo.is_publicly_listed(other) is False
