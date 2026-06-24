from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from voice_platform.job.models import Base


class UserCloudGpuProfileRow(Base):
    __tablename__ = "user_cloud_gpu_profiles"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    ssh_host: Mapped[str] = mapped_column(String(255), nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    ssh_user: Mapped[str] = mapped_column(String(64), nullable=False, default="root")
    auth_type: Mapped[str] = mapped_column(String(16), nullable=False, default="password")
    credential_enc: Mapped[str] = mapped_column(Text, nullable=False)
    remote_engine_root: Mapped[str] = mapped_column(String(512), nullable=False, default="/root/GPT-SoVITS")
    remote_platform_root: Mapped[str] = mapped_column(String(512), nullable=False, default="/root/GPT")
    remote_work_dir: Mapped[str] = mapped_column(String(512), nullable=False, default="/root/cloud_train_jobs")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
