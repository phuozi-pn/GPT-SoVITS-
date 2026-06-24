"""Resolve voice reference audio for GPT-SoVITS api_v2."""

from __future__ import annotations

from pathlib import Path

from voice_platform.config import get_settings
from voice_platform.engine.infer_weights import resolve_synthesis_weights
from voice_platform.engine.paths import host_path_to_container
from voice_platform.engine.train_dataset import (
    ENGINE_REF_MAX_SEC,
    ENGINE_REF_MIN_SEC,
    ensure_engine_ref_wav,
    wav_duration_sec,
)
from voice_platform.job.models import VoiceVersionRow
from voice_platform.storage.resolve import resolve_storage_uri


def _container_ref_path(voice: VoiceVersionRow) -> str | None:
    meta = voice.metadata_json or {}
    for key in ("engine_ref_audio_container", "engine_ref_audio_path"):
        value = meta.get(key)
        if value and str(value).startswith("/workspace/"):
            return str(value)
    uri = (voice.ref_audio_uri or "").strip()
    if uri.startswith("/workspace/"):
        return uri
    return None


def container_path_to_host(container: str) -> Path | None:
    """Map in-container ref path to host file under ENGINE_TRAIN_ROOT / platform mount."""
    if not container:
        return None
    normalized = container.replace("\\", "/")
    if not normalized.startswith("/"):
        return None

    settings = get_settings()
    engine_root = (settings.engine_train_root or "").strip()
    engine_container = (settings.engine_train_root_in_docker or "/workspace/GPT-SoVITS").rstrip("/")
    if engine_root and normalized.startswith(engine_container):
        rel = normalized[len(engine_container) :].lstrip("/")
        host = Path(engine_root) / rel
        if host.is_file():
            return host.resolve()

    platform_mount = (settings.engine_train_platform_mount or "/workspace/GPT").rstrip("/")
    if normalized.startswith(platform_mount):
        from voice_platform.engine.paths import platform_root

        rel = normalized[len(platform_mount) :].lstrip("/")
        host = platform_root() / rel
        if host.is_file():
            return host.resolve()
    return None


def ensure_host_ref_for_engine(host: Path) -> Path:
    """Ensure ref wav on disk fits api_v2 3–10s constraint (trim in place if needed)."""
    dur = wav_duration_sec(host)
    if ENGINE_REF_MIN_SEC <= dur <= ENGINE_REF_MAX_SEC:
        return host

    trimmed = host.parent / f"{host.stem}_tts9s{host.suffix}"
    if trimmed.is_file():
        trimmed_dur = wav_duration_sec(trimmed)
        if ENGINE_REF_MIN_SEC <= trimmed_dur <= ENGINE_REF_MAX_SEC:
            return trimmed

    ensure_engine_ref_wav(host, trimmed)
    return trimmed


def voice_ref_host_path(voice: VoiceVersionRow) -> Path | None:
    """Return an existing host file for ref audio, or None."""
    meta = voice.metadata_json or {}

    engine_host = meta.get("engine_ref_audio_path")
    if engine_host:
        path = Path(str(engine_host))
        if path.is_file():
            return path.resolve()
        host = container_path_to_host(str(engine_host))
        if host is not None:
            return host

    container = _container_ref_path(voice)
    if container:
        host = container_path_to_host(container)
        if host is not None:
            return host

    uri = (voice.ref_audio_uri or "").strip()
    if uri.startswith("local://"):
        try:
            return resolve_storage_uri(uri)
        except (FileNotFoundError, OSError):
            return None

    if uri:
        path = Path(uri)
        if path.is_file():
            return path.resolve()

    return None


def resolve_engine_ref_container(voice: VoiceVersionRow) -> str:
    """Container path for api_v2 ref_audio_path."""
    host = voice_ref_host_path(voice)
    if host is None:
        uri = voice.ref_audio_uri or "(missing)"
        raise RuntimeError(
            f"参考音频不存在或路径无效：{uri}。"
            "请在 Studio 重新训练/上传，或换一个可用音色。"
        )
    host = ensure_host_ref_for_engine(host)
    return host_path_to_container(str(host))


def voice_synth_ready(voice: VoiceVersionRow, *, engine_mock: bool | None = None) -> bool:
    """Whether this version can be used for real-engine synthesis."""
    settings = get_settings()
    mock_engine = settings.engine_mock if engine_mock is None else engine_mock
    meta = voice.metadata_json or {}

    if meta.get("mock") and not mock_engine:
        return False

    if mock_engine and meta.get("mock"):
        return True

    if voice_ref_host_path(voice) is None and _container_ref_path(voice) is None:
        return False

    if meta.get("mock"):
        return True

    return resolve_synthesis_weights(meta) is not None
