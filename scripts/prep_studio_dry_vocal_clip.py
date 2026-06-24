"""Trim a dry vocal wav to Studio quick-clone length (mono 32kHz, default 9s head)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{rest}"


def _ffmpeg_trim(src: Path, out: Path, *, start_sec: float, duration_sec: float, sample_rate: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    out.parent.mkdir(parents=True, exist_ok=True)
    if ffmpeg:
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            str(start_sec),
            "-i",
            str(src),
            "-t",
            str(duration_sec),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "ffmpeg failed")[-2000:])
        return

    wsl = shutil.which("wsl")
    if not wsl:
        raise RuntimeError("ffmpeg not found")
    staging = REPO / "data" / "temp" / "clip_src.wav"
    staging.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, staging)
    wsl_src = _to_wsl_path(staging)
    wsl_out = _to_wsl_path(out)
    inner = (
        f'ffmpeg -y -ss {start_sec} -i "{wsl_src}" -t {duration_sec} '
        f"-ac 1 -ar {sample_rate} -c:a pcm_s16le \"{wsl_out}\""
    )
    proc = subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "bash", "-lc", inner],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ffmpeg failed")[-2000:])


def _probe(path: Path) -> dict:
    with path.open("rb") as fh:
        with wave.open(fh, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return {
                "duration_sec": round(frames / float(rate), 2),
                "sample_rate": rate,
                "channels": wf.getnchannels(),
                "size_bytes": path.stat().st_size,
            }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src",
        type=Path,
        default=REPO / "infra/engine/samples/bilibili_BV1AcLQzBEGF_vocal.wav",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "infra/engine/samples/keyword_vocal_9s.wav",
    )
    parser.add_argument(
        "--ref-out",
        type=Path,
        default=REPO / "infra/engine/samples/keyword_vocal_9s_ref.txt",
    )
    parser.add_argument(
        "--ref-text",
        default="好好爱自己，就有人会爱你，这乐观的说词，幸福的样子，我感觉好真实。",
    )
    parser.add_argument("--start", type=float, default=0.0, help="Start offset in seconds")
    parser.add_argument("--duration", type=float, default=9.0, help="Clip length in seconds")
    parser.add_argument("--sample-rate", type=int, default=32000)
    parser.add_argument("--copy-public", action="store_true")
    args = parser.parse_args()

    if not args.src.is_file():
        raise SystemExit(f"Source not found: {args.src}")

    _ffmpeg_trim(
        args.src,
        args.out,
        start_sec=args.start,
        duration_sec=args.duration,
        sample_rate=args.sample_rate,
    )
    args.ref_out.write_text(args.ref_text.strip() + "\n", encoding="utf-8")

    if args.copy_public:
        public = REPO / "apps/web/public/samples"
        public.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.out, public / args.out.name)
        shutil.copy2(args.ref_out, public / args.ref_out.name)

    print(
        json.dumps(
            {"out": str(args.out), "ref_text": args.ref_text.strip(), **_probe(args.out)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
