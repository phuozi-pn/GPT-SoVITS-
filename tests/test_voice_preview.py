"""Voice preview URL resolution tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from domains.voices.preview import (
    resolve_asset_preview_audio_url,
    resolve_version_clone_demo_audio_url,
    resolve_version_preview_audio_url,
    resolve_version_source_audio_url,
)

VID = UUID("11111111-1111-1111-1111-111111111101")
ASSET_ID = UUID("33333333-3333-3333-3333-333333333301")


def test_resolve_version_preview_prefers_synth():
    session = MagicMock()
    row = SimpleNamespace(id=VID, ref_audio_uri="local://u/ref.wav", metadata_json={})
    with patch("domains.voices.preview.QualityReportRepository") as repo_cls:
        repo_cls.return_value.get.return_value = SimpleNamespace(
            synth_audio_url="http://x/synth.wav",
            ref_audio_url="http://x/ref.wav",
        )
        with patch("domains.voices.preview.resolve_public_url", side_effect=lambda u: u):
            url = resolve_version_preview_audio_url(session, row)
    assert url == "http://x/synth.wav"


def test_resolve_source_falls_back_to_voice_assets():
    session = MagicMock()
    row = SimpleNamespace(
        id=VID,
        voice_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        owner_user_id=UUID("00000000-0000-0000-0000-000000000001"),
        ref_audio_uri=None,
        metadata_json={},
    )
    asset = SimpleNamespace(storage_uri="local://u/upload.wav")
    with patch("domains.voices.preview.VoiceRepository") as voice_repo_cls:
        voice_repo_cls.return_value.list_assets_for_voice.return_value = [asset]
        with patch("domains.voices.preview.QualityReportRepository") as qr_cls:
            qr_cls.return_value.get.return_value = None
            with patch("domains.voices.preview.resolve_public_url", return_value="http://files/upload.wav"):
                url = resolve_version_source_audio_url(session, row)
    assert url == "http://files/upload.wav"


def test_resolve_source_prefers_linked_asset():
    session = MagicMock()
    row = SimpleNamespace(
        id=VID,
        voice_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        owner_user_id=UUID("00000000-0000-0000-0000-000000000001"),
        ref_audio_uri="local://u/ref.wav",
        metadata_json={"voice_asset_id": str(ASSET_ID)},
    )
    asset = SimpleNamespace(storage_uri="local://u/upload.wav")
    with patch("domains.voices.preview.VoiceRepository") as voice_repo_cls:
        voice_repo_cls.return_value.get_asset.return_value = asset
        with patch("domains.voices.preview.resolve_public_url", return_value="http://files/upload.wav"):
            url = resolve_version_source_audio_url(session, row)
    assert url == "http://files/upload.wav"


def test_resolve_clone_demo_from_quality_report():
    session = MagicMock()
    row = SimpleNamespace(id=VID, metadata_json={})
    with patch("domains.voices.preview.QualityReportRepository") as repo_cls:
        repo_cls.return_value.get.return_value = SimpleNamespace(
            synth_audio_url="http://x/synth.wav",
            ref_audio_url=None,
        )
        with patch("domains.voices.preview.resolve_public_url", return_value="http://x/synth.wav"):
            url = resolve_version_clone_demo_audio_url(session, row)
    assert url == "http://x/synth.wav"


def test_resolve_clone_demo_from_last_synth_metadata():
    session = MagicMock()
    row = SimpleNamespace(
        id=VID,
        metadata_json={"last_synth_audio_url": "local://u/last.wav"},
    )
    with patch("domains.voices.preview.QualityReportRepository") as repo_cls:
        repo_cls.return_value.get.return_value = None
        with patch("domains.voices.preview.VoiceCatalogRepository") as cat_cls:
            cat_cls.return_value.find_by_version.return_value = None
            with patch("domains.voices.preview.resolve_public_url", return_value="http://files/last.wav"):
                url = resolve_version_clone_demo_audio_url(session, row)
    assert url == "http://files/last.wav"


def test_resolve_version_preview_falls_back_to_stream_path(tmp_path):
    session = MagicMock()
    row = SimpleNamespace(id=VID, ref_audio_uri="/workspace/GPT-SoVITS/samples/x.wav", metadata_json={})
    host_file = tmp_path / "x.wav"
    host_file.write_bytes(b"RIFF")
    with patch("domains.voices.preview.VoiceRepository") as voice_repo_cls:
        voice_repo_cls.return_value.list_assets_for_voice.return_value = []
        with patch("domains.voices.preview.QualityReportRepository") as qr_cls:
            qr_cls.return_value.get.return_value = None
            with patch("domains.voices.preview.VoiceCatalogRepository") as cat_cls:
                cat_cls.return_value.find_by_version.return_value = None
                with patch("domains.voices.preview.resolve_public_url", return_value=None):
                    with patch("domains.voices.preview.voice_ref_host_path", return_value=host_file):
                        url = resolve_version_source_audio_url(session, row)
    assert url == f"/api/v1/voice-versions/{VID}/preview-audio"


def test_resolve_asset_preview_skips_engine_uri():
    assert resolve_asset_preview_audio_url("engine://samples/x.wav") is None
