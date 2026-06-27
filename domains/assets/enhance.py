"""Training asset speech enhancement (ffmpeg)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from domains.assets.convert import _to_wsl_path
from domains.assets.errors import AssetQcError


def _filter_chain(*, profile: str, target_lufs: float) -> str:
    """Conservative chain for dubbing training: EQ + light compression + loudness."""
    tp = -1.5
    lra = 11.0
    loudnorm = f"loudnorm=I={target_lufs}:TP={tp}:LRA={lra}"
    base = (
        "highpass=f=80,"
        "lowpass=f=12000,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=4,"
        "alimiter=limit=-1dB:level=false"
    )
    if profile == "clarity_denoise":
        return f"highpass=f=80,afftdn=nr=10:nf=-25,lowpass=f=12000,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=4,alimiter=limit=-1dB:level=false,{loudnorm}"
    if profile == "clarity":
        return f"{base},{loudnorm}"
    raise AssetQcError("ENHANCE_PROFILE_UNKNOWN", f"Unknown enhance profile: {profile}")


def _run_ffmpeg(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed")[-2000:]
        raise AssetQcError("AUDIO_ENHANCE_FAILED", detail)


def enhance_wav_in_place(
    path: Path,
    *,
    profile: str = "clarity",
    target_lufs: float = -18.0,
    sample_rate: int = 32000,
) -> dict[str, object]:
    """Enhance mono speech wav in place. Returns metadata; never raises if ffmpeg missing."""
    if not path.is_file():
        return {"applied": False, "reason": "file_missing"}

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        wsl = shutil.which("wsl")
        if not wsl:
            return {"applied": False, "reason": "ffmpeg_not_found"}
        return _enhance_via_wsl(path, profile=profile, target_lufs=target_lufs, sample_rate=sample_rate)

    tmp = path.with_name(f"{path.stem}.enhanced{path.suffix}")
    try:
        af = _filter_chain(profile=profile, target_lufs=target_lufs)
        _run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-af",
                af,
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                str(tmp),
            ]
        )
        if not tmp.is_file() or tmp.stat().st_size < 44:
            return {"applied": False, "reason": "empty_output"}
        tmp.replace(path)
        return {"applied": True, "profile": profile, "target_lufs": target_lufs}
    except AssetQcError as exc:
        tmp.unlink(missing_ok=True)
        return {"applied": False, "reason": exc.code, "detail": exc.message}
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        return {"applied": False, "reason": "io_error", "detail": str(exc)}


def _enhance_via_wsl(
    path: Path,
    *,
    profile: str,
    target_lufs: float,
    sample_rate: int,
) -> dict[str, object]:
    wsl = shutil.which("wsl")
    if not wsl:
        return {"applied": False, "reason": "ffmpeg_not_found"}

    tmp = path.with_name(f"{path.stem}.enhanced{path.suffix}")
    wsl_src = _to_wsl_path(path)
    wsl_dst = _to_wsl_path(tmp)
    af = _filter_chain(profile=profile, target_lufs=target_lufs)
    inner = (
        f'ffmpeg -y -i "{wsl_src}" -af "{af}" -ac 1 -ar {sample_rate} '
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
        tmp.unlink(missing_ok=True)
        detail = (proc.stderr or proc.stdout or "ffmpeg failed")[-500:]
        return {"applied": False, "reason": "AUDIO_ENHANCE_FAILED", "detail": detail}
    if not tmp.is_file():
        return {"applied": False, "reason": "empty_output"}
    try:
        tmp.replace(path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        return {"applied": False, "reason": "io_error", "detail": str(exc)}
    return {"applied": True, "profile": profile, "target_lufs": target_lufs, "via": "wsl"}
