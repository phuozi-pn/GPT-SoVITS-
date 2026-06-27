"""Asset speech enhancement tests."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from domains.assets.enhance import _filter_chain, enhance_wav_in_place


def _write_wav(path, *, duration_sec: float = 0.2, sample_rate: int = 32000) -> None:
    nframes = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x01" * nframes)


def test_filter_chain_clarity():
    chain = _filter_chain(profile="clarity", target_lufs=-18.0)
    assert "highpass=f=80" in chain
    assert "loudnorm=I=-18.0" in chain


def test_enhance_skips_without_ffmpeg(tmp_path, monkeypatch):
    wav = tmp_path / "a.wav"
    _write_wav(wav)
    monkeypatch.setattr("domains.assets.enhance.shutil.which", lambda name: None)
    meta = enhance_wav_in_place(wav)
    assert meta["applied"] is False
    assert meta["reason"] == "ffmpeg_not_found"


def test_enhance_applies_with_mock_ffmpeg(tmp_path):
    wav = tmp_path / "a.wav"
    _write_wav(wav)

    def fake_run(cmd: list[str]) -> None:
        _write_wav(Path(cmd[-1]), duration_sec=0.2)

    with patch("domains.assets.enhance.shutil.which", return_value="/usr/bin/ffmpeg"):
        with patch("domains.assets.enhance._run_ffmpeg", side_effect=fake_run):
            meta = enhance_wav_in_place(wav, profile="clarity")
    assert meta["applied"] is True
    assert meta["profile"] == "clarity"
    assert wav.is_file()
