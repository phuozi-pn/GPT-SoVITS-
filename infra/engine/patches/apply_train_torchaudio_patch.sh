#!/bin/bash
# Idempotent patch: 2-get-sv.py uses safe_torchaudio_load (same as inference/api_v2).
set -euo pipefail

ENGINE_ROOT="${ENGINE_ROOT:-/workspace/GPT-SoVITS}"
TARGET="${ENGINE_ROOT}/GPT_SoVITS/prepare_datasets/2-get-sv.py"

if [ ! -f "$TARGET" ]; then
  echo "ERROR: $TARGET not found (ENGINE_ROOT=$ENGINE_ROOT)"
  exit 1
fi

if grep -q 'safe_torchaudio_load' "$TARGET"; then
  echo "2-get-sv.py already patched (safe_torchaudio_load)"
  exit 0
fi

export TARGET
python3 - <<'PY'
from pathlib import Path
import os

target = Path(os.environ["TARGET"])
text = target.read_text(encoding="utf-8")
old_import = "from tools.my_utils import load_audio, clean_path"
new_import = "from tools.my_utils import load_audio, clean_path, safe_torchaudio_load"
if old_import not in text:
    raise SystemExit(f"Unexpected import line in {target}")
text = text.replace(old_import, new_import, 1)
old_load = "wav32k,sr0 = torchaudio.load(wav_path)"
new_load = "wav32k,sr0 = safe_torchaudio_load(wav_path)"
if old_load not in text:
    raise SystemExit(f"Unexpected torchaudio.load line in {target}")
text = text.replace(old_load, new_load, 1)
target.write_text(text, encoding="utf-8")
print(f"Patched {target}")
PY
