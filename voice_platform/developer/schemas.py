from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class ApiKeyCreatedResponse(BaseModel):
    key_id: UUID
    name: str
    key_prefix: str
    api_key: str
    scopes: list[str]
    created_at: datetime | None = None


class ApiKeySummary(BaseModel):
    key_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    revoked: bool
    last_used_at: datetime | None = None
    created_at: datetime | None = None


class OpenSynthesisRequest(BaseModel):
    voice_version_id: UUID
    text: str = Field(min_length=1, max_length=5000)
    format: str = "wav"
    ai_disclosure_ack: bool = True


class OpenSynthesisResponse(BaseModel):
    job_id: UUID
    status: str
    queue_position: int | None = None
