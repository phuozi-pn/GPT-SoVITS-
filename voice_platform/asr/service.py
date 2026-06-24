from __future__ import annotations

import logging
from pathlib import Path

from voice_platform.asr.base import AsrResult
from voice_platform.asr.factory import get_asr_provider
from voice_platform.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AssetAsrService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        if not self._settings.asset_asr_enabled:
            return False
        return get_asr_provider(self._settings) is not None

    def transcribe_clip(self, wav_path: Path) -> AsrResult:
        provider = get_asr_provider(self._settings)
        if provider is None:
            raise RuntimeError(
                "ASR unavailable: pip install 'voice-platform[asr]' or set ASR_MOCK=true"
            )
        language = self._settings.asset_asr_language
        clip_sec = self._settings.asset_asr_clip_sec
        logger.info(
            "asr transcribe path=%s provider=%s clip=%.1fs lang=%s",
            wav_path.name,
            provider.name,
            clip_sec,
            language,
        )
        return provider.transcribe(wav_path, language=language, clip_sec=clip_sec)

    def transcribe_segment(self, wav_path: Path) -> AsrResult:
        """Transcribe the full wav (used for per-segment cloud dataset prep)."""
        provider = get_asr_provider(self._settings)
        if provider is None:
            raise RuntimeError(
                "ASR unavailable: pip install 'voice-platform[asr]' or set ASR_MOCK=true"
            )
        language = self._settings.asset_asr_language
        return provider.transcribe(wav_path, language=language, clip_sec=0.0)
