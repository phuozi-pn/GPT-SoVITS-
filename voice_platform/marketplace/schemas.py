from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PublishEligibilityResponse(BaseModel):
    can_publish: bool
    invite_required: bool
    invited: bool
    on_waitlist: bool
    quality_gate: bool
    reason: str | None = None
    message: str | None = None


class WaitlistJoinRequest(BaseModel):
    contact: str = Field(default="", max_length=128)
    note: str = Field(default="", max_length=500)


class WaitlistJoinResponse(BaseModel):
    on_waitlist: bool
    message: str


class InviteRedeemRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class InviteRedeemResponse(BaseModel):
    invited: bool
    code: str
    message: str


class InviteCodeCreateRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    max_uses: int = Field(default=1, ge=1, le=10_000)
    note: str = Field(default="", max_length=200)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class InviteCodeSummary(BaseModel):
    invite_code_id: UUID
    code: str
    max_uses: int
    used_count: int
    note: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None


class WaitlistEntrySummary(BaseModel):
    waitlist_id: UUID
    user_id: UUID
    phone: str = ""
    contact: str
    note: str
    created_at: datetime | None = None


class WaitlistIssueRequest(BaseModel):
    code: str | None = Field(default=None, min_length=4, max_length=32)
    expires_in_days: int | None = Field(default=30, ge=1, le=365)


class WaitlistIssueResponse(BaseModel):
    waitlist_id: UUID
    user_id: UUID
    code: str
    message: str


class SellerAuthorizationStatsResponse(BaseModel):
    total_sales: int
    active_authorizations: int
    total_chars_used: int
    total_chars_quota: int
