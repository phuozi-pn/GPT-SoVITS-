from __future__ import annotations

from voice_platform.asr.base import AsrProvider
from voice_platform.asr.mock import MockAsrProvider
from voice_platform.config import Settings


def get_asr_provider(settings: Settings) -> AsrProvider | None:
    if settings.asset_asr_mock:
        return MockAsrProvider(settings)
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        return None
    from voice_platform.asr.faster_whisper import FasterWhisperAsrProvider

    return FasterWhisperAsrProvider(settings)
