#!/bin/bash
# Fix: torch.from_numpy fails with "expected np.ndarray (got numpy.ndarray)"
# on some AutoDL images (dual numpy / PyTorch ABI). Use torch.tensor instead.
set -euo pipefail

ENGINE_ROOT="${ENGINE_ROOT:-/workspace/GPT-SoVITS}"
TARGET="${ENGINE_ROOT}/GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py"

if [ ! -f "$TARGET" ]; then
  echo "ERROR: $TARGET not found (ENGINE_ROOT=$ENGINE_ROOT)"
  exit 1
fi

if grep -q 'tolist(), dtype=torch.float32)' "$TARGET"; then
  echo "2-get-hubert-wav32k.py already patched (hubert numpy)"
  exit 0
fi

export TARGET
python3 - <<'PY'
from pathlib import Path
import os

target = Path(os.environ["TARGET"])
text = target.read_text(encoding="utf-8")
old_lines = [
    "    tensor_wav16 = torch.from_numpy(tmp_audio)",
    "    tensor_wav16 = torch.tensor(np.ascontiguousarray(tmp_audio, dtype=np.float32))",
    "    _arr = np.ascontiguousarray(tmp_audio, dtype=np.float32)\n    tensor_wav16 = torch.frombuffer(_arr.tobytes(), dtype=torch.float32).clone()",
]
new = (
    "    _arr = np.ascontiguousarray(tmp_audio, dtype=np.float32)\n"
    "    tensor_wav16 = torch.tensor(_arr.reshape(-1).tolist(), dtype=torch.float32)"
)
patched = False
for old in old_lines:
    if old in text:
        text = text.replace(old, new, 1)
        patched = True
        break
if not patched:
    raise SystemExit(f"Unexpected content in {target} (tensor_wav16 line missing)")
target.write_text(text, encoding="utf-8")
print(f"Patched {target}")
PY
