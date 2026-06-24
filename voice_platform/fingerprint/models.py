from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from voice_platform.job.models import Base


class AudioFingerprintRow(Base):
    __tablename__ = "audio_fingerprints"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    hashes_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    hash_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
