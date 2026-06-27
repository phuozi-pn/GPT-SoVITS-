"""Marketplace owner display name on catalog entries."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

from domains.marketplace.service import MarketplaceService

OWNER = UUID("11111111-1111-1111-1111-111111111111")


def test_entry_response_includes_owner_display_name():
    session = MagicMock()
    svc = MarketplaceService(session)

    entry = MagicMock()
    entry.id = UUID("22222222-2222-2222-2222-222222222222")
    entry.voice_version_id = UUID("33333333-3333-3333-3333-333333333333")
    entry.owner_user_id = OWNER
    entry.title = "test-voice"
    entry.description = ""
    entry.tags_json = ["gentle", "mature"]
    entry.featured = True
    entry.status = "published"
    entry.demo_text = ""
    entry.demo_audio_url = None
    entry.demo_job_id = None
    entry.license_type = "personal_non_commercial"
    entry.price_cents = 0
    entry.billing_unit = "per_1k_chars"
    entry.included_chars = 50000
    entry.prohibited_domains_json = []
    entry.policy_version = 1

    ver = MagicMock()
    ver.id = entry.voice_version_id
    ver.voice_id = UUID("44444444-4444-4444-4444-444444444444")
    voice = MagicMock()
    voice.name = "demo-voice"

    profile_repo = MagicMock()
    profile_repo.get.return_value = MagicMock(display_name="Star Voice", bio="")

    with patch("domains.marketplace.service.UserProfileRepository", return_value=profile_repo):
        svc._versions.get = MagicMock(return_value=ver)
        svc._voices.get_voice = MagicMock(return_value=voice)
        item = svc._entry_response(entry, viewer_user_id=OWNER)

    assert item is not None
    assert item.owner_display_name == "Star Voice"
    assert item.tags == ["gentle", "mature"]
