from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=2048)
    is_public: bool | None = None


class AvatarGenerateResponse(BaseModel):
    avatar_url: str
    prompt: str = ""


class UserPublicProfileResponse(BaseModel):
    user_id: UUID
    display_name: str
    bio: str
    avatar_url: str | None = None
    published_voice_count: int
    is_self: bool = False


class UserDirectoryEntry(BaseModel):
    user_id: UUID
    display_name: str
    bio: str
    avatar_url: str | None = None
    published_voice_count: int


class MessageCreateRequest(BaseModel):
    recipient_user_id: UUID
    body: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    message_id: UUID
    sender_user_id: UUID
    recipient_user_id: UUID
    body: str
    read_at: datetime | None = None
    created_at: datetime


class ConversationPreviewResponse(BaseModel):
    peer_user_id: UUID
    peer_display_name: str
    last_message: str
    last_at: datetime
    unread_count: int
