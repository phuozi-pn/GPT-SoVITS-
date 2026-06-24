#!/usr/bin/env python3
"""REQ-019 watermark MOS spike — measure LSB embed distortion on synthetic speech-like WAV."""

from __future__ import annotations

import math
import struct
import wave
from io import BytesIO

from voice_platform.watermark.embedder import build_watermark_payload, embed_watermark, extract_watermark


def _sine_wav(*, seconds: float = 3.0, sample_rate: int = 32000, freq: float = 220.0) -> bytes:
    nframes = int(sample_rate * seconds)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(nframes):
            t = i / sample_rate
            sample = int(12000 * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack("<h", sample))
    return buf.getvalue()


def _read_samples(wav_bytes: bytes) -> list[int]:
    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    return list(struct.unpack(f"<{len(frames) // 2}h", frames))


def snr_db(original: list[int], modified: list[int]) -> float:
    n = min(len(original), len(modified))
    signal_power = sum(float(o) ** 2 for o in original[:n]) / max(n, 1)
    noise_power = sum(float(o - m) ** 2 for o, m in zip(original[:n], modified[:n])) / max(n, 1)
    if noise_power <= 0:
        return float("inf")
    return 10 * math.log10(signal_power / noise_power)


def max_abs_delta(original: list[int], modified: list[int]) -> int:
    n = min(len(original), len(modified))
    return max(abs(o - m) for o, m in zip(original[:n], modified[:n])) if n else 0


def main() -> None:
    wav = _sine_wav()
    payload = build_watermark_payload(user_id="spike-user", voice_id="spike-voice", job_id="spike-job")
    watermarked = embed_watermark(wav, payload)
    orig = _read_samples(wav)
    mod = _read_samples(watermarked)
    extracted = extract_watermark(watermarked)

    print("=== Watermark MOS Spike (LSB) ===")
    print(f"SNR (full clip): {snr_db(orig, mod):.2f} dB")
    print(f"Max |delta| sample: {max_abs_delta(orig, mod)}")
    print(f"Payload round-trip: {extracted is not None}")
    if extracted:
        print(f"  user_id={extracted.user_id} voice_id={extracted.voice_id}")
    print()
    print("Interpretation:")
    print("- LSB on <=1KB samples: SNR typically >40dB, max delta=1 — imperceptible in listening tests")
    print("- Production: prefer spread-spectrum or segment-hash watermark for robustness (see docs)")


if __name__ == "__main__":
    main()
