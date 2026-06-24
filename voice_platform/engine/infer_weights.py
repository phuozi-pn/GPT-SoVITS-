"""Resolve GPT-SoVITS api_v2 weight paths per VoiceVersion (avoid cross-voice bleed)."""

from __future__ import annotations

from pathlib import Path

from voice_platform.config import get_settings
from voice_platform.engine.paths import weights_path_for_api


def read_v2pro_base_weights(engine_root: Path) -> tuple[str, str] | None:
    """Read v2Pro pretrained paths from tts_infer_v2pro.yaml (not `custom` finetunes)."""
    yaml_path = engine_root / "GPT_SoVITS/configs/tts_infer_v2pro.yaml"
    if not yaml_path.is_file():
        return None

    in_block = False
    gpt: str | None = None
    sovits: str | None = None
    for raw in yaml_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped == "v2Pro:":
            in_block = True
            continue
        if not in_block:
            continue
        if stripped and not line.startswith((" ", "\t")):
            break
        if "t2s_weights_path:" in stripped:
            gpt = stripped.split(":", 1)[1].strip().strip("'\"")
        elif "vits_weights_path:" in stripped:
            sovits = stripped.split(":", 1)[1].strip().strip("'\"")
    if gpt and sovits:
        return gpt.replace("\\", "/"), sovits.replace("\\", "/")
    return None


def resolve_synthesis_weights(meta: dict) -> tuple[str, str] | None:
    """Weights to load before each /tts — always explicit, never rely on stale api state."""
    custom = weights_path_for_api(meta or {})
    if custom[0] and custom[1]:
        return custom[0], custom[1]

    settings = get_settings()
    if settings.engine_default_gpt_weights and settings.engine_default_sovits_weights:
        return (
            settings.engine_default_gpt_weights.strip(),
            settings.engine_default_sovits_weights.strip(),
        )

    train_mode = (meta or {}).get("train_mode", "")
    if train_mode == "quick_clone" or (meta or {}).get("engine_use_base_weights"):
        root = (settings.engine_train_root or "").strip()
        if root:
            parsed = read_v2pro_base_weights(Path(root))
            if parsed:
                return parsed
    return None
