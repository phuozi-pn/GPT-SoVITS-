from __future__ import annotations

import re
import wave
from pathlib import Path


def wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def _read_wav(path: Path) -> tuple[bytes, int, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    return frames, rate, channels, sampwidth


def _write_wav(path: Path, *, frames: bytes, rate: int, channels: int, sampwidth: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(frames)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；.!?])", text.replace("\n", ""))
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    if not out:
        out = [text.strip()]
    return out


def bucket_sentences(sentences: list[str], n_buckets: int) -> list[str]:
    if n_buckets <= 0:
        return []
    if n_buckets == 1:
        return ["".join(sentences)]
    total = sum(len(s) for s in sentences) or 1
    target = total / n_buckets
    buckets: list[str] = []
    current: list[str] = []
    current_len = 0
    bucket_idx = 0
    for sent in sentences:
        current.append(sent)
        current_len += len(sent)
        if bucket_idx < n_buckets - 1 and current_len >= target:
            buckets.append("".join(current))
            current = []
            current_len = 0
            bucket_idx += 1
    if current:
        buckets.append("".join(current))
    while len(buckets) < n_buckets:
        buckets.append(sentences[-1] if sentences else "。")
    return buckets[:n_buckets]


def slice_wav_dataset(
    *,
    wav_path: Path,
    ref_text: str,
    out_dir: Path,
    segment_sec: float = 12.0,
    min_segment_sec: float = 6.0,
) -> list[tuple[str, str]]:
    """Slice long wav + ref_text into (segment_wav_path, text) pairs."""
    frames, rate, channels, sampwidth = _read_wav(wav_path)
    frame_bytes = channels * sampwidth
    total_frames = len(frames) // frame_bytes
    duration = total_frames / rate

    if duration <= 15.0:
        seg_path = out_dir / wav_path.name
        _write_wav(seg_path, frames=frames, rate=rate, channels=channels, sampwidth=sampwidth)
        return [(str(seg_path.resolve()), ref_text.strip())]

    seg_frames = max(int(segment_sec * rate), 1)
    min_frames = int(min_segment_sec * rate)
    chunks: list[bytes] = []
    for start in range(0, total_frames, seg_frames):
        end = min(start + seg_frames, total_frames)
        if end - start < min_frames and chunks:
            chunks[-1] += frames[start * frame_bytes : end * frame_bytes]
        else:
            chunks.append(frames[start * frame_bytes : end * frame_bytes])

    sentences = split_sentences(ref_text)
    texts = bucket_sentences(sentences, len(chunks))
    pairs: list[tuple[str, str]] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (chunk, text) in enumerate(zip(chunks, texts)):
        if not text.strip():
            continue
        seg_path = out_dir / f"seg_{i:04d}.wav"
        _write_wav(seg_path, frames=chunk, rate=rate, channels=channels, sampwidth=sampwidth)
        pairs.append((str(seg_path.resolve()), text.strip()))
    if not pairs:
        raise RuntimeError("dataset slice produced no segments")
    return pairs
