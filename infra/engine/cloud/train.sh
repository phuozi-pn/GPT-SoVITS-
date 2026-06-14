#!/usr/bin/env bash
# Fine-tune on rented GPU (AutoDL / cloud). Not for Windows local Docker.
set -euo pipefail

WAV="${1:?usage: train.sh <wav> [out_dir] [job_id]}"
OUT_DIR="${2:-./train_out}"
JOB_ID="${3:-cloud-$(date +%Y%m%d%H%M%S)}"
ENGINE_ROOT="${ENGINE_ROOT:-$HOME/GPT-SoVITS}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="${PLATFORM_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

PREPARE="$PLATFORM_ROOT/infra/engine/scripts/prepare_train_dataset.py"
SPIKE="$PLATFORM_ROOT/infra/engine/scripts/spike_train_v2pro.py"
CONFIG="$PLATFORM_ROOT/infra/engine/train-v2pro-spike.json"

if [[ ! -f "$ENGINE_ROOT/webui.py" ]]; then
  echo "ENGINE_ROOT invalid: $ENGINE_ROOT (set ENGINE_ROOT= path to GPT-SoVITS clone)" >&2
  exit 1
fi
if [[ ! -f "$WAV" ]]; then
  echo "wav not found: $WAV" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
DATASET="$OUT_DIR/dataset"
EXP="cloud_${JOB_ID//[^a-zA-Z0-9_]/_}"
EXP="${EXP:0:32}"

echo "== 1/2 prepare dataset (slice + FunASR) =="
python "$PREPARE" \
  --engine-root "$ENGINE_ROOT" \
  --wav "$WAV" \
  --out-dir "$DATASET" \
  --language "${TRAIN_ASR_LANGUAGE:-zh}"

echo "== 2/2 spike train (4+4 epochs default) =="
python "$SPIKE" \
  --engine-root "$ENGINE_ROOT" \
  --job-id "$JOB_ID" \
  --list-file "$DATASET/train.list" \
  --wav-dir "$DATASET/segments" \
  --exp-name "$EXP" \
  --config "$CONFIG" \
  --result "$OUT_DIR/result.json" \
  --clean

echo ""
echo "Done."
echo "  result: $OUT_DIR/result.json"
echo "  weights: $ENGINE_ROOT/GPT_weights_v2Pro/  $ENGINE_ROOT/SoVITS_weights_v2Pro/"
echo "  scp example:"
echo "    scp -P <port> root@<host>:$ENGINE_ROOT/GPT_weights_v2Pro/${EXP}*.ckpt ."
echo "    scp -P <port> root@<host>:$ENGINE_ROOT/SoVITS_weights_v2Pro/${EXP}*.pth ."
