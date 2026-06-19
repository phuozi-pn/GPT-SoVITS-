#!/usr/bin/env python3
"""Start API for Playwright E2E (expects Postgres + Redis on localhost)."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.chdir(ROOT)
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql+psycopg://voice:voice_dev@127.0.0.1:5432/voice_platform")
    env.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
    env.setdefault("DEV_SKIP_AUTH", "true")
    env.setdefault("ENGINE_MOCK", "true")
    env.setdefault("TRAIN_MOCK", "true")
    env.setdefault("PAYMENT_CHECKOUT_ASYNC", "false")
    env.setdefault("STORAGE_ROOT", "./data/storage-e2e")

    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"], check=True, env=env)

    print("Applying DB migrations (incl. E2E catalog seed)…", flush=True)
    from apps.api.main import _run_migrations

    _run_migrations()

    print("Starting API on http://127.0.0.1:8001…", flush=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8001"],
        env=env,
    )

    def _shutdown(*_: object) -> None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _shutdown)

    sys.exit(proc.wait())


if __name__ == "__main__":
    main()
