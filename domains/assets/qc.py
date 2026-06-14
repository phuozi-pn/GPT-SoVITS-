from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

from voice_platform.config import get_settings
from voice_platform.job.schemas import QcIssue, QcResult

_ALLOWED_EXT = {".wav", ".flac", ".mp3"}


@dataclass
class AudioProbe:
    duration_sec: float
    sample_rate: int
    channels: int


class AssetQcError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def probe_wav(path: Path) -> AudioProbe:
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            if rate <= 0:
                raise AssetQcError("QC_DECODE_FAILED", "Invalid sample rate in wav")
            duration = frames / float(rate)
            return AudioProbe(duration_sec=duration, sample_rate=rate, channels=channels)
    except wave.Error as exc:
        raise AssetQcError("QC_DECODE_FAILED", f"Cannot decode wav: {exc}") from exc


def run_qc(
    *,
    path: Path,
    filename: str,
    ref_text: str | None = None,
) -> QcResult:
    settings = get_settings()
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise AssetQcError("INVALID_AUDIO_FORMAT", f"Unsupported format: {ext or '(none)'}")

    if ext != ".wav":
        raise AssetQcError(
            "INVALID_AUDIO_FORMAT",
            "W2 MVP only decodes wav; convert flac/mp3 to wav before upload",
        )

    probe = probe_wav(path)
    issues: list[QcIssue] = []

    min_dur = (
        settings.qc_dev_min_duration_sec
        if settings.qc_dev_relax_duration
        else settings.qc_min_duration_sec
    )
    max_dur = settings.qc_max_duration_sec

    if probe.duration_sec < min_dur:
        issues.append(
            QcIssue(
                code="QC_DURATION_TOO_SHORT",
                message=f"Duration {probe.duration_sec:.1f}s < required {min_dur:.0f}s",
            )
        )
    if probe.duration_sec > max_dur:
        issues.append(
            QcIssue(
                code="QC_DURATION_TOO_LONG",
                message=f"Duration {probe.duration_sec:.1f}s > max {max_dur:.0f}s",
            )
        )
    if probe.sample_rate < settings.qc_min_sample_rate:
        issues.append(
            QcIssue(
                code="QC_SAMPLE_RATE_LOW",
                message=f"Sample rate {probe.sample_rate} < {settings.qc_min_sample_rate}",
            )
        )

    status = "passed" if not issues else "failed"
    return QcResult(
        status=status,
        duration_sec=round(probe.duration_sec, 2),
        sample_rate=probe.sample_rate,
        channels=probe.channels,
        issues=issues,
        ref_text=ref_text,
    )
