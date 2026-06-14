#!/bin/bash
# Prepare ref wav + train.list for platform fine-tune spike (run inside engine container).
set -euo pipefail

ENGINE_ROOT="${ENGINE_ROOT:-/workspace/GPT-SoVITS}"
PLATFORM_ROOT="${PLATFORM_ROOT:-/workspace/GPT}"

if [ ! -d "$PLATFORM_ROOT/infra/engine/samples" ]; then
  echo "ERROR: $PLATFORM_ROOT not mounted. Restart with engine_run_with_platform_mount.ps1"
  exit 1
fi

mkdir -p "$ENGINE_ROOT/samples"
cp "$PLATFORM_ROOT/infra/engine/samples/ref_zh_zero_shot.wav" "$ENGINE_ROOT/samples/"
cat > "$ENGINE_ROOT/samples/train.list" << 'EOF'
/workspace/GPT-SoVITS/samples/ref_zh_zero_shot.wav|spk0|zh|大家好，我是测试用户，今天我们来测试一下语音合成功能。
EOF
echo "Prepared $ENGINE_ROOT/samples/train.list"
