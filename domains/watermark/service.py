"""REQ-019 Digital watermark detection service."""

from __future__ import annotations

from voice_platform.watermark.embedder import extract_watermark
from voice_platform.watermark.schemas import WatermarkPayload


class WatermarkServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class WatermarkService:
    """Watermark detection use case — wraps embedder as domain service."""

    def detect(self, wav_bytes: bytes) -> WatermarkPayload | None:
        """Extract digital watermark from WAV audio bytes.

        Returns WatermarkPayload if found, None otherwise.
        Raises WatermarkServiceError for unsupported formats.
        """
        return extract_watermark(wav_bytes)
