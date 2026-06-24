#!/usr/bin/env bash
# Fine-tune from pre-built dataset (local slice + ASR already done). Skips prepare step.
set -euo pipefail

DATASET_DIR="${1:?usage: train_from_dataset.sh <dataset_dir> [out_dir] [job_id]}"
OUT_DIR="${2:-./train_out}"
JOB_ID="${3:-cloud-$(date +%Y%m%d%H%M%S)}"
ENGINE_ROOT="${ENGINE_ROOT:-$HOME/GPT-SoVITS}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="${PLATFORM_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

SPIKE="$PLATFORM_ROOT/infra/engine/scripts/spike_train_v2pro.py"
CONFIG="$PLATFORM_ROOT/infra/engine/train-v2pro-spike.json"
LIST_FILE="$DATASET_DIR/train.list"
WAV_DIR="$DATASET_DIR/segments"

if [[ ! -f "$ENGINE_ROOT/webui.py" ]]; then
  echo "ENGINE_ROOT invalid: $ENGINE_ROOT" >&2
  exit 1
fi
if [[ ! -f "$LIST_FILE" ]]; then
  echo "train.list not found: $LIST_FILE" >&2
  exit 1
fi
if [[ ! -d "$WAV_DIR" ]]; then
  echo "segments dir not found: $WAV_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
EXP="cloud_${JOB_ID//[^a-zA-Z0-9_]/_}"
EXP="${EXP:0:32}"

PYTHON="${CLOUD_TRAIN_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  done
fi
if [[ -z "$PYTHON" ]]; then
  echo "python3/python not found on remote GPU (set CLOUD_TRAIN_PYTHON)" >&2
  exit 127
fi
echo "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

echo "== spike train from pre-built dataset (skip slice/ASR, FP32) =="
export is_half=False
"$PYTHON" "$SPIKE" \
  --engine-root "$ENGINE_ROOT" \
  --job-id "$JOB_ID" \
  --list-file "$LIST_FILE" \
  --wav-dir "$WAV_DIR" \
  --exp-name "$EXP" \
  --config "$CONFIG" \
  --result "$OUT_DIR/result.json" \
  --clean

echo ""
echo "Done."
echo "  result: $OUT_DIR/result.json"
