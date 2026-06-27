"""Resolve HTTP preview URLs for trained voice versions and assets."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.config import get_settings
from voice_platform.engine.ref_audio import voice_ref_host_path
from voice_platform.job.repository import QualityReportRepository, VoiceCatalogRepository, VoiceRepository
from voice_platform.storage.local import LocalStorage
from voice_platform.storage.urls import resolve_public_url


def version_preview_stream_path(voice_version_id) -> str:
    return f"/api/v1/voice-versions/{voice_version_id}/preview-audio"


def _resolve_ref_audio_url(voice_version_row) -> str | None:
    url = resolve_public_url(voice_version_row.ref_audio_uri)
    if url:
        return url

    host = voice_ref_host_path(voice_version_row)
    if host is not None and host.is_file():
        storage_root = Path(get_settings().storage_root).resolve()
        try:
            rel = host.resolve().relative_to(storage_root)
            return LocalStorage().public_url(rel.as_posix())
        except ValueError:
            return version_preview_stream_path(voice_version_row.id)

    return None


def resolve_version_source_audio_url(session: Session, voice_version_row) -> str | None:
    """Uploaded / reference material used before or during clone (原素材)."""
    meta = voice_version_row.metadata_json or {}
    voices = VoiceRepository(session)

    asset_id_raw = meta.get("voice_asset_id")
    if asset_id_raw:
        try:
            asset_id = UUID(str(asset_id_raw))
        except ValueError:
            asset_id = None
        if asset_id:
            asset = voices.get_asset(asset_id)
            if asset:
                url = resolve_public_url(asset.storage_uri)
                if url:
                    return url

    voice_id = getattr(voice_version_row, "voice_id", None)
    owner_user_id = getattr(voice_version_row, "owner_user_id", None)
    if voice_id and owner_user_id:
        for asset in voices.list_assets_for_voice(voice_id, owner_user_id):
            url = resolve_public_url(asset.storage_uri)
            if url:
                return url

    qr = QualityReportRepository(session).get(voice_version_row.id)
    if qr and qr.ref_audio_url:
        return resolve_public_url(qr.ref_audio_url) or qr.ref_audio_url

    return _resolve_ref_audio_url(voice_version_row)


def resolve_version_clone_demo_audio_url(session: Session, voice_version_row) -> str | None:
    """Synthesized showcase clip after clone/train (克隆合成样例)."""
    qr = QualityReportRepository(session).get(voice_version_row.id)
    if qr and qr.synth_audio_url:
        url = resolve_public_url(qr.synth_audio_url)
        if url:
            return url

    meta = voice_version_row.metadata_json or {}
    for key in ("last_synth_audio_url", "preview_synth_url"):
        raw = meta.get(key)
        if not raw:
            continue
        url = resolve_public_url(str(raw))
        if url:
            return url

    catalog = VoiceCatalogRepository(session).find_by_version(voice_version_row.id)
    if catalog and catalog.demo_audio_url:
        return resolve_public_url(catalog.demo_audio_url)

    return None


def resolve_version_preview_audio_url(session: Session, voice_version_row) -> str | None:
    """Backward-compatible single preview: prefer clone synth, else source."""
    synth = resolve_version_clone_demo_audio_url(session, voice_version_row)
    if synth:
        return synth
    return resolve_version_source_audio_url(session, voice_version_row)


def resolve_asset_preview_audio_url(storage_uri: str | None) -> str | None:
    if not storage_uri or storage_uri.startswith("engine://"):
        return None
    return resolve_public_url(storage_uri)
