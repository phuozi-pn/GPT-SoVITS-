from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AsrResult:
    text: str
    provider: str
    clip_sec: float


class AsrProvider(ABC):
    name: str

    @abstractmethod
    def transcribe(self, wav_path: Path, *, language: str, clip_sec: float) -> AsrResult:
        """Transcribe up to clip_sec seconds from the start of wav_path."""
