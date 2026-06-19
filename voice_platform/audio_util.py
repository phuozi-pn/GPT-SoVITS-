from __future__ import annotations

import struct
import wave
from io import BytesIO


def pitch_shift_wav(wav_bytes: bytes, pitch_factor: float) -> bytes:
    """Shift pitch without changing sample rate header. pitch_factor > 1 = higher pitch."""
    if abs(pitch_factor - 1.0) < 0.01:
        return wav_bytes

    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        nch, sw, rate, nframes, _, _ = wf.getparams()
        frames = wf.readframes(nframes)

    if sw != 2 or nch != 1:
        return wav_bytes

    samples = struct.unpack(f"<{nframes}h", frames)
    dst_len = max(1, int(len(samples) / pitch_factor))
    out: list[int] = []
    for i in range(dst_len):
        src_idx = i * pitch_factor
        idx = int(src_idx)
        frac = src_idx - idx
        if idx + 1 < len(samples):
            val = int(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
        else:
            val = samples[min(idx, len(samples) - 1)]
        out.append(max(-32768, min(32767, val)))

    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{len(out)}h", *out))
    return buf.getvalue()


def silence_wav(duration_sec: float, sample_rate: int = 32000) -> bytes:
    """Generate a silent WAV chunk of the specified duration."""
    nframes = int(sample_rate * duration_sec)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{nframes}h", *([0] * nframes)))
    return buf.getvalue()


def concat_wav(chunks: list[bytes]) -> bytes:
    if not chunks:
        raise ValueError("no wav chunks")
    if len(chunks) == 1:
        return chunks[0]

    with wave.open(BytesIO(chunks[0]), "rb") as first:
        params = first.getparams()
        parts = [first.readframes(first.getnframes())]

    for chunk in chunks[1:]:
        with wave.open(BytesIO(chunk), "rb") as wf:
            if wf.getparams()[:3] != params[:3]:
                raise ValueError("wav format mismatch during concat")
            parts.append(wf.readframes(wf.getnframes()))

    buf = BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        for part in parts:
            out.writeframes(part)
    return buf.getvalue()
