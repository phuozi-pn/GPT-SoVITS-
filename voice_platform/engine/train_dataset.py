from __future__ import annotations

import wave
from pathlib import Path

from voice_platform.engine.dataset_slice import slice_wav_dataset, wav_duration_sec


def parse_train_list_line(line: str) -> tuple[str, str] | None:
    """Parse GPT-SoVITS .list line: wav|speaker|lang|text."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split("|", 3)
    if len(parts) < 4:
        return None
    path, _spk, _lang, text = parts
    text = text.strip()
    if not text:
        return None
    return path, text


def parse_train_list(content: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in content.splitlines():
        parsed = parse_train_list_line(line)
        if parsed:
            pairs.append(parsed)
    return pairs


def filter_pairs_by_duration(
    pairs: list[tuple[str, str]],
    *,
    min_sec: float = 1.0,
    max_sec: float = 30.0,
) -> list[tuple[str, str]]:
    kept: list[tuple[str, str]] = []
    for path, text in pairs:
        p = Path(path)
        if not p.is_file():
            continue
        dur = wav_duration_sec(p)
        if min_sec <= dur <= max_sec:
            kept.append((path, text))
    return kept


def trim_wav_copy(src: Path, dst: Path, *, max_sec: float = 9.0) -> Path:
    """Copy first max_sec of wav to dst (for api_v2 ref 3–10s constraint)."""
    with wave.open(str(src), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        max_frames = min(wf.getnframes(), int(max_sec * rate))
        frames = wf.readframes(max_frames)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(frames)
    return dst


def pick_infer_reference(
    pairs: list[tuple[str, str]],
    *,
    out_dir: Path | None = None,
    min_sec: float = 3.0,
    max_sec: float = 10.0,
    target_sec: float = 8.0,
) -> tuple[str, str]:
    """Pick a segment suitable for api_v2 zero-shot ref (3–10s, aligned text)."""
    if not pairs:
        raise RuntimeError("no segments for infer reference")

    scored: list[tuple[float, str, str]] = []
    for path, text in pairs:
        p = Path(path)
        if not p.is_file():
            continue
        dur = wav_duration_sec(p)
        if min_sec <= dur <= max_sec:
            scored.append((abs(dur - target_sec), path, text))

    if scored:
        scored.sort(key=lambda x: x[0])
        _, path, text = scored[0]
        return path, text

    # Fallback: trim the shortest segment that is long enough to contain min_sec.
    by_dur = sorted(
        ((wav_duration_sec(Path(p)), p, t) for p, t in pairs if Path(p).is_file()),
        key=lambda x: x[0],
    )
    if not by_dur:
        raise RuntimeError("no readable wav segments for infer reference")

    _dur, path, text = by_dur[0]
    src = Path(path)
    if out_dir is None:
        out_dir = src.parent
    trimmed = trim_wav_copy(src, out_dir / f"ref_{src.stem}_9s.wav", max_sec=max_sec - 1.0)
    return str(trimmed.resolve()), text


def build_dataset_pairs(
    *,
    wav_path: Path,
    ref_text: str,
    out_dir: Path,
    use_asr: bool,
    asr_threshold_sec: float = 15.0,
) -> list[tuple[str, str]]:
    """Short clip: single segment + user ref_text. Long clip: caller must run ASR prep."""
    duration = wav_duration_sec(wav_path)
    if not use_asr or duration <= asr_threshold_sec:
        return slice_wav_dataset(wav_path=wav_path, ref_text=ref_text, out_dir=out_dir)
    raise RuntimeError(
        "long audio requires ASR dataset preparation; call prepare_train_dataset.py first"
    )
