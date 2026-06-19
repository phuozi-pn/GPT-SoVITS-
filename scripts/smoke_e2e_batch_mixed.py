"""Batch-only E2E: CSV with one sensitive line → partial success + manifest failures.

  python scripts/smoke_e2e_batch_mixed.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV = REPO / "scripts" / "fixtures" / "guzhenren_batch_mixed.csv"
SCRIPT = REPO / "scripts" / "smoke_e2e_guzhenren.py"


def _load_main():
    spec = importlib.util.spec_from_file_location("smoke_e2e_guzhenren", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


if __name__ == "__main__":
    sys.argv = [
        str(SCRIPT),
        "--skip-single",
        "--csv",
        str(CSV),
        "--expect-failed-min",
        "1",
        "--expect-succeeded-min",
        "1",
    ]
    sys.exit(_load_main()())
