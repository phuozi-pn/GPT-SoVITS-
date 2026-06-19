from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KycStatusResponse(BaseModel):
    verified: bool
    verified_at: datetime | None = None
    required: bool
    provider: str | None = None


class KycSubmitRequest(BaseModel):
    real_name: str = Field(min_length=2, max_length=32)
    id_number: str = Field(min_length=18, max_length=18)

    @field_validator("real_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        name = v.strip()
        if not name:
            raise ValueError("real_name required")
        return name

    @field_validator("id_number")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        return v.strip().upper()


class KycSubmitResponse(BaseModel):
    verified: bool
    message: str
    audit_id: UUID


class KycAuditEntry(BaseModel):
    audit_id: UUID
    user_id: UUID
    action: str
    status: str
    provider: str
    message: str | None = None
    real_name_masked: str | None = None
    id_number_last4: str | None = None
    created_at: datetime


class AdminKycVerifyRequest(BaseModel):
    note: str | None = Field(default=None, max_length=200)


class AdminKycUserSummary(BaseModel):
    user_id: UUID
    phone: str
    verified: bool
    verified_at: datetime | None = None
    created_at: datetime
