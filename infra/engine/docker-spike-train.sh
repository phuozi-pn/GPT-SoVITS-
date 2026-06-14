#!/bin/bash
# Manual v2Pro fine-tune spike inside engine container.
# Prereq: ref audio + list file under samples/ (see samples/README.md).
set -euo pipefail

ENGINE_ROOT="${ENGINE_ROOT:-/workspace/GPT-SoVITS}"
PLATFORM_ROOT="${PLATFORM_ROOT:-/workspace/GPT}"
JOB_ID="${JOB_ID:-manual-spike-$(date +%s)}"
EXP_NAME="${EXP_NAME:-platform_${JOB_ID//-/}}"
LIST_FILE="${LIST_FILE:-${ENGINE_ROOT}/samples/train.list}"
WAV_DIR="${WAV_DIR:-${ENGINE_ROOT}/samples}"
CONFIG="${CONFIG:-${PLATFORM_ROOT}/infra/engine/train-v2pro-spike.json}"
RESULT="${RESULT:-/tmp/spike_train_${JOB_ID}.json}"
SPIKE_FROM_STEP="${SPIKE_FROM_STEP:-all}"
SPIKE_CLEAN="${SPIKE_CLEAN:-}"

mkdir -p "$(dirname "$RESULT")"
bash "${PLATFORM_ROOT}/infra/engine/patches/apply_train_torchaudio_patch.sh"

extra_args=()
if [ "$SPIKE_FROM_STEP" != "all" ]; then
  extra_args+=(--from-step "$SPIKE_FROM_STEP")
fi
if [ -n "$SPIKE_CLEAN" ]; then
  extra_args+=(--clean)
fi

python "${PLATFORM_ROOT}/infra/engine/scripts/spike_train_v2pro.py" \
  --engine-root "$ENGINE_ROOT" \
  --job-id "$JOB_ID" \
  --list-file "$LIST_FILE" \
  --wav-dir "$WAV_DIR" \
  --exp-name "$EXP_NAME" \
  --config "$CONFIG" \
  --result "$RESULT" \
  "${extra_args[@]}"

echo "Spike result: $RESULT"
cat "$RESULT"
