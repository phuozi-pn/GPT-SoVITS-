from __future__ import annotations

from pydantic import BaseModel, Field


class WatermarkPayload(BaseModel):
    """Metadata embedded as watermark in exported audio."""
    user_id: str = Field(min_length=1, max_length=64)
    voice_id: str = Field(min_length=1, max_length=64)
    job_id: str = Field(min_length=1, max_length=64)
    timestamp: str = Field(min_length=1, max_length=32)  # ISO 8601

    def to_json_str(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json_str(cls, raw: str) -> WatermarkPayload:
        return cls.model_validate_json(raw)
