from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from voice_platform.engine.paths import platform_root

_DEFAULT_SPIKE_REL = Path("infra/engine/train-v2pro-spike.json")


@lru_cache(maxsize=1)
def load_spike_train_config() -> dict:
    path = platform_root() / _DEFAULT_SPIKE_REL
    if not path.is_file():
        return {"gpt_epochs": 12, "sovits_epochs": 12}
    return json.loads(path.read_text(encoding="utf-8"))


def spike_epoch_label(cfg: dict | None = None) -> str:
    cfg = cfg or load_spike_train_config()
    gpt = int(cfg.get("gpt_epochs", 12))
    sov = int(cfg.get("sovits_epochs", 12))
    return f"{gpt}+{sov}"


def estimate_cloud_train_minutes(*, segment_count: int | None, cfg: dict | None = None) -> tuple[int, int]:
    """Rough wall-clock range on a mid-range GPU (preprocess + GPT + SoVITS)."""
    cfg = cfg or load_spike_train_config()
    gpt = int(cfg.get("gpt_epochs", 12))
    sov = int(cfg.get("sovits_epochs", 12))
    segs = max(int(segment_count or 30), 1)
    # preprocess ~0.5min + ~0.4min per epoch block scaled by segments
    base = 8 + segs // 8
    scale = (gpt + sov) / 12.0
    low = max(15, int(base * scale * 0.85))
    high = max(low + 10, int(base * scale * 1.35))
    return low, high
