"""Compliance export watermark metadata tests."""

from __future__ import annotations

from domains.compliance.export import apply_compliance_label
from voice_platform.watermark.schemas import WatermarkPayload


def test_apply_compliance_label_includes_watermark_metadata():
    wav = b"RIFF"  # invalid wav — rhythm label will fail, use minimal approach
    # Build minimal valid wav for test
    import io
    import struct
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(struct.pack("<h", 0) * 3200)
    wav_bytes = buf.getvalue()

    wm = WatermarkPayload(
        user_id="user-1",
        voice_id="voice-1",
        job_id="job-1",
        timestamp="2026-06-22T00:00:00+00:00",
    )
    _, meta = apply_compliance_label(wav_bytes, sample_rate=32000, watermark=wm)
    assert meta["watermark_user_id"] == "user-1"
    assert meta["watermark_job_id"] == "job-1"
    assert meta["watermark_voice_id"] == "voice-1"
