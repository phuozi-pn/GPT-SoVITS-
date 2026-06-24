"""Convert Bilibili download (mp4/m4a) to Studio-ready mono WAV."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path(r"C:\Users\panta\Desktop\bilibili_downloads")
DEFAULT_OUT = REPO / "infra" / "engine" / "samples" / "bilibili_BV1AcLQzBEGF_vocal.wav"
DEFAULT_REF = REPO / "infra" / "engine" / "samples" / "bilibili_BV1AcLQzBEGF_ref.txt"
OPENING_REF = (
    "好好爱自己，就有人会爱你，这乐观的说词，幸福的样子，我感觉好真实，找不到形容词。"
)


def _find_ffmpeg() -> str:
    for name in ("ffmpeg", "ffmpeg.exe"):
        found = shutil.which(name)
        if found:
            return found
    wsl = shutil.which("wsl")
    if wsl:
        return "wsl"
    raise RuntimeError("ffmpeg not found (install ffmpeg or use WSL)")


def _to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{rest}"


def _run_ffmpeg(ffmpeg: str, src: Path, out: Path, *, sample_rate: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if ffmpeg == "wsl":
        staging = REPO / "data" / "temp" / "studio_import_src.mp4"
        staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, staging)
        wsl_src = _to_wsl_path(staging)
        wsl_out = _to_wsl_path(out)
        inner = (
            f'ffmpeg -y -i "{wsl_src}" -vn -ac 1 -ar {sample_rate} '
            f'-c:a pcm_s16le "{wsl_out}"'
        )
        cmd = ["wsl", "-d", "Ubuntu-22.04", "bash", "-lc", inner]
    else:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-vn",
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
        err = (proc.stderr or proc.stdout or "ffmpeg failed")[-2000:]
        raise RuntimeError(err)


def _probe_wav(path: Path) -> dict:
    with path.open("rb") as fh:
        import wave

        with wave.open(fh, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            duration = frames / float(rate) if rate else 0.0
    return {
        "path": str(path),
        "duration_sec": round(duration, 2),
        "sample_rate": rate,
        "channels": channels,
        "size_bytes": path.stat().st_size,
    }


def resolve_source(path: Path | None, bv: str | None) -> Path:
    if path and path.is_file():
        return path
    folder = path if path and path.is_dir() else DEFAULT_SRC
    if bv:
        matches = sorted(folder.glob(f"*{bv}*.mp4")) + sorted(folder.glob(f"*{bv}*.m4a"))
        if matches:
            return matches[0]
    matches = sorted(folder.glob("*.mp4")) + sorted(folder.glob("*.m4a"))
    if not matches:
        raise FileNotFoundError(f"No mp4/m4a under {folder}")
    return matches[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, help="Source mp4/m4a or download folder")
    parser.add_argument("--bv", default="BV1AcLQzBEGF", help="Bilibili BV id for glob")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ref-out", type=Path, default=DEFAULT_REF)
    parser.add_argument("--ref-text", default=OPENING_REF)
    parser.add_argument("--sample-rate", type=int, default=32000)
    parser.add_argument("--copy-public", action="store_true", help="Also copy to apps/web/public/samples")
    args = parser.parse_args()

    src = resolve_source(args.src, args.bv)
    ffmpeg = _find_ffmpeg()
    _run_ffmpeg(ffmpeg, src, args.out, sample_rate=args.sample_rate)

    args.ref_out.parent.mkdir(parents=True, exist_ok=True)
    args.ref_out.write_text(args.ref_text.strip() + "\n", encoding="utf-8")

    if args.copy_public:
        public_dir = REPO / "apps" / "web" / "public" / "samples"
        public_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.out, public_dir / args.out.name)
        shutil.copy2(args.ref_out, public_dir / args.ref_out.name)

    info = _probe_wav(args.out)
    print(json.dumps({"source": str(src), "ref_text": args.ref_text, **info}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
