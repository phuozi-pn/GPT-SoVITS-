"""Install faster-whisper when ASR is enabled and not in mock mode."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _sync_dotenv(repo: Path) -> None:
    """Load .env into os.environ (same precedence as platform_start.ps1)."""
    env_path = repo / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ[key.strip()] = val.strip()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    _sync_dotenv(repo)
    os.chdir(repo)

    from voice_platform.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.asset_asr_enabled:
        print("asr: disabled (ASR_ENABLED=false)")
        return 0
    if settings.asset_asr_mock:
        print("asr: mock mode (ASR_MOCK=true)")
        return 0

    try:
        import faster_whisper  # noqa: F401

        print("asr: faster-whisper ready")
        return 0
    except ImportError:
        pass

    print("asr: installing voice-platform[asr] (first run may take a few minutes)...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", f"{repo}[asr]"],
        cwd=str(repo),
    )
    import faster_whisper  # noqa: F401

    print("asr: faster-whisper installed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"asr: install failed ({exc.returncode})", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:
        print(f"asr: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
