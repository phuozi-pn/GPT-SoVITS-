from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FingerprintEnrollRequest(BaseModel):
    """Register a fingerprint for an exported audio file."""

    job_id: UUID = Field(description="Export/synthesis job ID this fingerprint belongs to")
    user_id: UUID | None = Field(default=None, description="User who generated the audio")
    voice_id: UUID | None = Field(default=None, description="Voice used for synthesis")
    storage_url: str | None = Field(default=None, max_length=1024, description="Where the audio is stored")


class FingerprintEnrollResponse(BaseModel):
    fingerprint_id: UUID
    hash_count: int = Field(description="Number of audio hash peaks enrolled")
    enrolled_at: datetime


class FingerprintSearchRequest(BaseModel):
    """Search for matching fingerprints by uploading audio."""

    # file is handled as multipart upload


class FingerprintMatch(BaseModel):
    fingerprint_id: UUID
    job_id: UUID
    user_id: UUID | None = None
    voice_id: UUID | None = None
    enrolled_at: datetime
    similarity: float = Field(ge=0.0, le=1.0, description="Match similarity score")


class FingerprintSearchResponse(BaseModel):
    matches: list[FingerprintMatch] = Field(default_factory=list)
    search_duration_ms: float = Field(default=0.0)


class FingerprintStatusResponse(BaseModel):
    total_enrolled: int
    engine: str = "spectral-peak-v1"
