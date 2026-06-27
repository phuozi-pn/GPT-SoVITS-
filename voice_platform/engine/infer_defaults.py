"""Default api_v2 infer params when VoiceVersion metadata omits them."""

from __future__ import annotations

DEFAULT_TEXT_SPLIT_METHOD = "cut0"
DEFAULT_TEMPERATURE = 0.78
DEFAULT_SPEED_FACTOR = 1.05
DEFAULT_TOP_P = 1.0
DEFAULT_TUNE_PRESET = "cut0_t078_sp105"

STABLE_TEXT_SPLIT_METHOD = "cut0"
STABLE_TEMPERATURE = 0.68
STABLE_SPEED_FACTOR = 1.0
STABLE_TOP_P = 0.95
STABLE_TUNE_PRESET = "cut0_t068_topp095"


def default_infer_metadata() -> dict[str, str | float]:
    return {
        "text_split_method": DEFAULT_TEXT_SPLIT_METHOD,
        "temperature": DEFAULT_TEMPERATURE,
        "speed_factor": DEFAULT_SPEED_FACTOR,
        "top_p": DEFAULT_TOP_P,
        "tune_preset": DEFAULT_TUNE_PRESET,
    }


def stable_infer_metadata() -> dict[str, str | float]:
    return {
        "text_split_method": STABLE_TEXT_SPLIT_METHOD,
        "temperature": STABLE_TEMPERATURE,
        "speed_factor": STABLE_SPEED_FACTOR,
        "top_p": STABLE_TOP_P,
        "tune_preset": STABLE_TUNE_PRESET,
    }


def quick_clone_infer_metadata() -> dict[str, str | float]:
    """Zero-shot quick clone: lower temp / speed reduces metallic artifacts."""
    return stable_infer_metadata()
