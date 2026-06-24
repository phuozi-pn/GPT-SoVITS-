from __future__ import annotations

from pathlib import Path

from voice_platform.asr.base import AsrProvider, AsrResult
from voice_platform.config import Settings


class MockAsrProvider(AsrProvider):
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self._text = settings.asset_asr_mock_text

    def transcribe(self, wav_path: Path, *, language: str, clip_sec: float) -> AsrResult:
        return AsrResult(text=self._text, provider=self.name, clip_sec=clip_sec)
