from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from domains.assets.errors import AssetQcError

CONVERTIBLE_EXTENSIONS = {".m4a", ".aac", ".mp3", ".flac"}


def _to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{rest}"


def convert_to_wav(src: Path, dst: Path, *, sample_rate: int = 32000) -> None:
    """Decode compressed audio to mono 16-bit PCM wav."""
    if not src.is_file():
        raise AssetQcError("AUDIO_CONVERT_FAILED", f"Source not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(dst),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "ffmpeg failed")[-2000:]
            raise AssetQcError("AUDIO_CONVERT_FAILED", detail)
        return

    wsl = shutil.which("wsl")
    if not wsl:
        raise AssetQcError(
            "FFMPEG_REQUIRED",
            "m4a/mp3/flac upload requires ffmpeg on PATH or WSL",
        )

    wsl_src = _to_wsl_path(src)
    wsl_dst = _to_wsl_path(dst)
    inner = (
        f'ffmpeg -y -i "{wsl_src}" -ac 1 -ar {sample_rate} '
        f'-c:a pcm_s16le "{wsl_dst}"'
    )
    proc = subprocess.run(
        ["wsl", "bash", "-lc", inner],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed")[-2000:]
        raise AssetQcError("AUDIO_CONVERT_FAILED", detail)


def ensure_wav(path: Path, *, sample_rate: int = 32000) -> Path:
    """Return a wav path, converting in place when needed."""
    ext = path.suffix.lower()
    if ext == ".wav":
        return path
    if ext not in CONVERTIBLE_EXTENSIONS:
        raise AssetQcError("INVALID_AUDIO_FORMAT", f"Unsupported format: {ext or '(none)'}")

    out = path.with_suffix(".wav")
    convert_to_wav(path, out, sample_rate=sample_rate)
    if out.resolve() != path.resolve():
        path.unlink(missing_ok=True)
    return out
