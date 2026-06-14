#!/bin/bash
# 与上游 scripts/docker-api-v2-start.sh 一致
set -euo pipefail
pip install -q 'starlette<1.0.0' 2>/dev/null || true
cd /workspace/GPT-SoVITS
exec python api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_v2pro.yaml
