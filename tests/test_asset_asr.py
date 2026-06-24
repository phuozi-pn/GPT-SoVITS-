from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from domains.assets.ref_text import resolve_upload_ref_text
from voice_platform.config import get_settings


def _write_wav(path: Path, *, duration_sec: float = 5.0, sample_rate: int = 32000) -> None:
    nframes = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * nframes)


def test_resolve_prefers_manual_ref(tmp_path, monkeypatch):
    wav = tmp_path / "a.wav"
    _write_wav(wav)
    text, auto, provider, issues = resolve_upload_ref_text(wav, "  手动文本  ")
    assert text == "手动文本"
    assert auto is False
    assert provider is None
    assert issues == []


def test_resolve_auto_asr_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("ASR_MOCK", "true")
    monkeypatch.setenv("ASR_MOCK_TEXT", "自动识别的一句台词。")
    get_settings.cache_clear()

    wav = tmp_path / "a.wav"
    _write_wav(wav)
    text, auto, provider, issues = resolve_upload_ref_text(wav, None)
    assert text == "自动识别的一句台词。"
    assert auto is True
    assert provider == "mock"
    assert issues == []
    get_settings.cache_clear()


def test_resolve_asr_unavailable_without_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("ASR_MOCK", "false")
    monkeypatch.setenv("ASR_ENABLED", "true")
    get_settings.cache_clear()

    wav = tmp_path / "a.wav"
    _write_wav(wav)

    with patch("voice_platform.asr.factory.get_asr_provider", return_value=None):
        text, auto, provider, issues = resolve_upload_ref_text(wav, None)

    assert text is None
    assert auto is False
    assert any(i.code == "ASR_UNAVAILABLE" for i in issues)
    get_settings.cache_clear()
