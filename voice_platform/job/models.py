from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
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


class VoiceCatalogEntryRow(Base):
    __tablename__ = "voice_catalog_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_json: Mapped[list[Any]] = mapped_column("tags", JSONB, default=list)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    demo_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    demo_audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    license_type: Mapped[str] = mapped_column(String(32), nullable=False, default="personal_non_commercial")
    price_cents: Mapped[int] = mapped_column(nullable=False, default=0)
    billing_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="per_1k_chars")
    included_chars: Mapped[int] = mapped_column(nullable=False, default=50000)
    prohibited_domains_json: Mapped[list[Any]] = mapped_column(
        "prohibited_domains", JSONB, default=list
    )
    policy_version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceGrantRow(Base):
    __tablename__ = "voice_grants"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    granter_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    grantee_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="synthesize")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceAuthorizationRow(Base):
    __tablename__ = "voice_authorizations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    catalog_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    seller_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    buyer_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    license_type: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="per_1k_chars")
    char_quota_total: Mapped[int] = mapped_column(nullable=False, default=0)
    char_quota_used: Mapped[int] = mapped_column(nullable=False, default=0)
    price_paid_cents: Mapped[int] = mapped_column(nullable=False, default=0)
    payment_ref: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentOrderRow(Base):
    __tablename__ = "payment_orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    authorization_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    catalog_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    buyer_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    seller_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="paid")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    provider_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceComplaintRow(Base):
    __tablename__ = "voice_complaints"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    catalog_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    voice_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    reporter_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceQualityReportRow(Base):
    __tablename__ = "voice_quality_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)
    eval_sentence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ref_audio_url: Mapped[str | None] = mapped_column(Text)
    synth_audio_url: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(64), nullable=False, default="mock_embedding")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AbVoteRow(Base):
    __tablename__ = "ab_votes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    voter_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    pick_slot: Mapped[str] = mapped_column(String(8), nullable=False)
    slot_a_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    slot_b_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    picked_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchLineRow(Base):
    """批量合成行级状态 — 支持实时进度、失败重试、Worker 崩溃恢复。"""

    __tablename__ = "batch_lines"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    line_index: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    audio_url: Mapped[str | None] = mapped_column(Text)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    export_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    label_type: Mapped[str | None] = mapped_column(String(32))
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
