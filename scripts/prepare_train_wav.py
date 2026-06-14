from __future__ import annotations

"""Convert PCM .raw → training .wav (trim to target duration).

.raw has no header — you must know sample rate / channels (or use --probe).

Examples:
  python scripts/prepare_train_wav.py "C:\\...\\file.raw" --probe
  python scripts/prepare_train_wav.py file.raw -o train_10min.wav --sample-rate 22050 --channels 1 --trim-min 10
"""

import argparse
import struct
import wave
from pathlib import Path

COMMON_RATES = (16000, 22050, 32000, 44100, 48000)


def duration_sec(byte_len: int, sample_rate: int, channels: int, sampwidth: int = 2) -> float:
    frame_bytes = channels * sampwidth
    return byte_len / frame_bytes / sample_rate


def probe_raw(path: Path, channels: int = 1) -> None:
    nbytes = path.stat().st_size
    print(f"File: {path}")
    print(f"Size: {nbytes} bytes ({nbytes / 1024 / 1024:.1f} MiB)")
    print(f"Assuming 16-bit PCM, channels={channels}:")
    for rate in COMMON_RATES:
        dur = duration_sec(nbytes, rate, channels)
        print(f"  {rate:5d} Hz -> {dur/60:.2f} min ({dur:.0f}s)")


def raw_to_wav(
    *,
    raw_path: Path,
    out_path: Path,
    sample_rate: int,
    channels: int,
    trim_sec: float | None,
    offset_sec: float,
) -> dict:
    data = raw_path.read_bytes()
    frame_bytes = channels * 2
    if len(data) % frame_bytes != 0:
        data = data[: len(data) - (len(data) % frame_bytes)]

    start = int(offset_sec * sample_rate) * frame_bytes
    data = data[start:]
    total_sec = duration_sec(len(data), sample_rate, channels)

    if trim_sec is not None and trim_sec > 0:
        max_bytes = int(trim_sec * sample_rate) * frame_bytes
        data = data[:max_bytes]

    out_sec = duration_sec(len(data), sample_rate, channels)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data)

    return {
        "output": str(out_path),
        "sample_rate": sample_rate,
        "channels": channels,
        "duration_sec": round(out_sec, 2),
        "source_duration_sec": round(total_sec, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare .raw PCM for platform train upload")
    parser.add_argument("input", type=Path, help=".raw or copy as .raw")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output .wav path")
    parser.add_argument("--sample-rate", type=int, default=44100)
    parser.add_argument("--channels", type=int, default=1, choices=(1, 2))
    parser.add_argument("--trim-min", type=float, default=10.0, help="Keep first N minutes (0=all)")
    parser.add_argument("--offset-sec", type=float, default=0.0, help="Skip leading seconds")
    parser.add_argument("--probe", action="store_true", help="Print duration guesses and exit")
    args = parser.parse_args()

    raw_path = args.input.resolve()
    if not raw_path.is_file():
        print(f"Not found: {raw_path}")
        return 2

    if args.probe:
        probe_raw(raw_path, channels=args.channels)
        return 0

    out = args.output or raw_path.with_name(f"{raw_path.stem}_train.wav")
    trim_sec = args.trim_min * 60.0 if args.trim_min > 0 else None
    info = raw_to_wav(
        raw_path=raw_path,
        out_path=out.resolve(),
        sample_rate=args.sample_rate,
        channels=args.channels,
        trim_sec=trim_sec,
        offset_sec=args.offset_sec,
    )
    print("Wrote:", info["output"])
    print(f"  duration: {info['duration_sec']}s @ {info['sample_rate']}Hz ch={info['channels']}")
    print()
    print("Next (cloud GPU train):")
    print(f'  bash infra/engine/cloud/train.sh "{info["output"]}" /root/train_out my-job')
    print("  See docs/architecture/2026-06-10-云端GPU训练指南.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
