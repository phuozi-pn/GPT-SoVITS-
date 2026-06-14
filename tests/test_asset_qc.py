from __future__ import annotations

import io
import wave

import pytest

from domains.assets.qc import AssetQcError, run_qc
from voice_platform.config import get_settings


def _write_wav(path, *, duration_sec: float, sample_rate: int = 32000) -> None:
    nframes = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * nframes)


def test_qc_passes_relaxed_duration(tmp_path, monkeypatch):
    monkeypatch.setenv("QC_DEV_RELAX_DURATION", "true")
    monkeypatch.setenv("QC_DEV_MIN_DURATION_SEC", "3")
    get_settings.cache_clear()

    wav = tmp_path / "sample.wav"
    _write_wav(wav, duration_sec=5.0)
    result = run_qc(path=wav, filename="sample.wav", ref_text="你好")
    assert result.status == "passed"
    assert result.ref_text == "你好"
    get_settings.cache_clear()


def test_qc_fails_duration_too_short(tmp_path, monkeypatch):
    monkeypatch.setenv("QC_DEV_RELAX_DURATION", "false")
    monkeypatch.setenv("QC_MIN_DURATION_SEC", "480")
    get_settings.cache_clear()

    wav = tmp_path / "short.wav"
    _write_wav(wav, duration_sec=60.0)
    result = run_qc(path=wav, filename="short.wav")
    assert result.status == "failed"
    assert any(i.code == "QC_DURATION_TOO_SHORT" for i in result.issues)
    get_settings.cache_clear()


def test_qc_rejects_mp3(tmp_path):
    mp3 = tmp_path / "x.mp3"
    mp3.write_bytes(b"ID3")
    with pytest.raises(AssetQcError) as exc:
        run_qc(path=mp3, filename="x.mp3")
    assert exc.value.code == "INVALID_AUDIO_FORMAT"
