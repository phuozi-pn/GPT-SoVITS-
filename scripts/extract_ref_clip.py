"""Extract 3–10s ref clip from a long wav for manual ref_text alignment.

Usage:
  python scripts/extract_ref_clip.py data/train_raw/train_20min.wav --start-sec 120 --duration-sec 8
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path


def extract_clip(src: Path, dst: Path, *, start_sec: float, duration_sec: float) -> dict:
    with wave.open(str(src), "rb") as wf:
        rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        start_frame = int(start_sec * rate)
        nframes = min(int(duration_sec * rate), wf.getnframes() - start_frame)
        wf.setpos(start_frame)
        frames = wf.readframes(nframes)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sampwidth)
        out.setframerate(rate)
        out.writeframes(frames)
    return {
        "src": str(src),
        "out": str(dst),
        "start_sec": start_sec,
        "duration_sec": round(nframes / rate, 2),
        "sample_rate": rate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract ref clip from long wav")
    parser.add_argument("wav", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--start-sec", type=float, default=60.0)
    parser.add_argument("--duration-sec", type=float, default=8.0)
    args = parser.parse_args()
    out = args.output or Path("data/tune_refs") / f"{args.wav.stem}_{int(args.start_sec)}s.wav"
    info = extract_clip(args.wav, out, start_sec=args.start_sec, duration_sec=args.duration_sec)
    print(info)
    print("IMPORTANT: ref_text must match spoken content in this clip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
