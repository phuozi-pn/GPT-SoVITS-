from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from voice_platform.job.models import Base


class UserProfileRow(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserMessageRow(Base):
    __tablename__ = "user_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sender_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    recipient_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    # When set, this message is associated with a "conversation with <peer>" for the recipient,
    # even if sender_user_id is a system actor.
    conversation_peer_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceDownloadEventRow(Base):
    __tablename__ = "voice_download_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    catalog_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    download_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
