"""Tests for engine ref audio resolution."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from voice_platform.engine.ref_audio import resolve_engine_ref_container, voice_ref_host_path, voice_synth_ready
from voice_platform.job.models import VoiceVersionRow


def _voice(**kwargs) -> VoiceVersionRow:
    row = VoiceVersionRow(
        id=uuid4(),
        voice_id=uuid4(),
        owner_user_id=uuid4(),
        version=1,
        model_tag="v2pro",
    )
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def test_voice_ref_host_path_local_uri(tmp_path, monkeypatch):
    wav = tmp_path / "u" / "training" / "clip.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"RIFF")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    row = _voice(ref_audio_uri="local://u/training/clip.wav")
    assert voice_ref_host_path(row) == wav.resolve()


def test_resolve_engine_ref_container_trims_long_host_ref(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    samples = engine / "samples"
    samples.mkdir(parents=True)
    long_ref = samples / "cloud_ref_long.wav"
    import wave

    with wave.open(str(long_ref), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(b"\x00\x00" * (32000 * 60))

    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    monkeypatch.setenv("ENGINE_TRAIN_ROOT_IN_DOCKER", "/workspace/GPT-SoVITS")
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    container = "/workspace/GPT-SoVITS/samples/cloud_ref_long.wav"
    row = _voice(
        ref_audio_uri=container,
        metadata_json={"engine_ref_audio_path": container},
    )
    resolved = resolve_engine_ref_container(row)
    assert resolved.endswith("cloud_ref_long_tts9s.wav")
    trimmed = samples / "cloud_ref_long_tts9s.wav"
    assert trimmed.is_file()
    with wave.open(str(trimmed), "rb") as wf:
        dur = wf.getnframes() / wf.getframerate()
    assert 8.9 <= dur <= 9.1
    get_settings.cache_clear()


def test_resolve_engine_ref_container_rejects_missing(monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", "/nonexistent")
    from voice_platform.config import get_settings

    get_settings.cache_clear()
    row = _voice(ref_audio_uri="local://dev/training/sample.wav", metadata_json={"mock": True})
    with pytest.raises(RuntimeError, match="参考音频不存在"):
        resolve_engine_ref_container(row)


def test_voice_synth_ready_rejects_mock_when_engine_real(monkeypatch):
    monkeypatch.setenv("ENGINE_MOCK", "false")
    from voice_platform.config import get_settings

    get_settings.cache_clear()
    row = _voice(ref_audio_uri="local://dev/training/sample.wav", metadata_json={"mock": True})
    assert voice_synth_ready(row) is False
