#!/usr/bin/env bash
# Start API for Playwright E2E (expects Postgres + Redis on localhost).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://voice:voice_dev@127.0.0.1:5432/voice_platform}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export DEV_SKIP_AUTH="${DEV_SKIP_AUTH:-true}"
export ENGINE_MOCK="${ENGINE_MOCK:-true}"
export TRAIN_MOCK="${TRAIN_MOCK:-true}"
export PAYMENT_CHECKOUT_ASYNC="${PAYMENT_CHECKOUT_ASYNC:-false}"
export STORAGE_ROOT="${STORAGE_ROOT:-./data/storage-e2e}"

if ! command -v python >/dev/null 2>&1; then
  echo "python not found" >&2
  exit 1
fi

pip install -e ".[dev]" -q

echo "Applying DB migrations (incl. E2E catalog seed)…"
python -c "from apps.api.main import _run_migrations; _run_migrations()"

echo "Starting API on http://127.0.0.1:8001…"
exec python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8001
