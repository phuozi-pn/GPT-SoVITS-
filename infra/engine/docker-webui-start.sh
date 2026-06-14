#!/bin/bash
# 与上游 clone 内 scripts/docker-webui-start.sh 保持一致
# 每次新容器启动 WebUI 前执行（自动 pip + webui）
set -euo pipefail
pip install -q 'starlette<1.0.0'
cd /workspace/GPT-SoVITS
echo "Open http://127.0.0.1:9874 (not 0.0.0.0)"
exec python webui.py
