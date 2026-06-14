from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class VoiceRow(Base):
    __tablename__ = "voices"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="voice")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentRow(Base):
    __tablename__ = "consents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceAssetRow(Base):
    __tablename__ = "voice_assets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_result_json: Mapped[dict[str, Any] | None] = mapped_column("qc_result", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceVersionRow(Base):
    __tablename__ = "voice_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    model_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_uri: Mapped[str | None] = mapped_column(String(512))
    ref_audio_uri: Mapped[str | None] = mapped_column(String(512))
    ref_text: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectRoleRow(Base):
    __tablename__ = "project_roles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    job_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
