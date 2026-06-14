from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from voice_platform.quota.schemas import QuotaSummary


_PHONE_RE = __import__("re").compile(r"^1[3-9]\d{9}$")


class SmsSendRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        phone = v.strip()
        if not _PHONE_RE.match(phone):
            raise ValueError("invalid phone")
        return phone


class LoginRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11)
    code: str = Field(min_length=6, max_length=6)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        phone = v.strip()
        if not _PHONE_RE.match(phone):
            raise ValueError("invalid phone")
        return phone

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        code = v.strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError("invalid code")
        return code


class UserInfo(BaseModel):
    user_id: UUID
    phone: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_days: int
    user: UserInfo
    quota: QuotaSummary | None = None


class SmsSendResponse(BaseModel):
    message: str = "验证码已发送"
    mock_code: str | None = None
