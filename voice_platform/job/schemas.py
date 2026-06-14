from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


JOB_SCHEMA_VERSION = "1.0.0"
MODEL_TAG_V2PRO = "gsv-v2pro-20250606"


class JobType(StrEnum):
    PREPROCESS = "preprocess"
    TRAIN = "train"
    SYNTHESIZE = "synthesize"
    BATCH = "batch"
    EXPORT = "export"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InferPayload(BaseModel):
    voice_version_id: UUID
    text: str
    format: str = "wav"
    sample_rate: int = 32000


class BatchLinePayload(BaseModel):
    index: int
    role: str
    text: str
    voice_version_id: UUID


class BatchPayload(BaseModel):
    project_id: UUID | None = None
    lines: list[BatchLinePayload] = Field(min_length=1, max_length=500)


class ImportEngineWeightsRequest(BaseModel):
    """Register cloud/local engine weights as a VoiceVersion."""
    voice_id: UUID | None = None
    voice_name: str = Field(default="导入音色", min_length=1, max_length=128)
    label: str = Field(default="", max_length=64)
    engine_gpt_weights: str = Field(min_length=1, max_length=512)
    engine_sovits_weights: str = Field(min_length=1, max_length=512)
    ref_audio_host_path: str = Field(min_length=1, max_length=1024)
    ref_text: str = Field(min_length=1, max_length=2000)
    text_split_method: str = Field(default="cut0", pattern="^(cut0|cut1|cut2|cut3|cut4|cut5)$")
    temperature: float = Field(default=0.78, ge=0.1, le=2.0)
    speed_factor: float = Field(default=1.05, ge=0.5, le=2.0)
    top_p: float = Field(default=1.0, ge=0.1, le=1.0)
    model_tag: str = MODEL_TAG_V2PRO


class VoiceVersionSummary(BaseModel):
    voice_version_id: UUID
    voice_id: UUID
    voice_name: str
    version: int
    model_tag: str
    label: str | None = None
    ref_text: str | None = None
    imported: bool = False
    created_at: datetime | None = None


class VoiceSummary(BaseModel):
    voice_id: UUID
    name: str
    version_count: int = 0
    latest_version_id: UUID | None = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ProjectRoleRequest(BaseModel):
    role_name: str = Field(min_length=1, max_length=64)
    voice_version_id: UUID


class ProjectRoleResponse(BaseModel):
    role_id: UUID
    project_id: UUID
    role_name: str
    voice_version_id: UUID


class ProjectResponse(BaseModel):
    project_id: UUID
    name: str
    roles: list[ProjectRoleResponse] = Field(default_factory=list)


class CatalogPublishRequest(BaseModel):
    voice_version_id: UUID
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    featured: bool = False


class CatalogEntryResponse(BaseModel):
    catalog_id: UUID
    voice_version_id: UUID
    voice_id: UUID
    voice_name: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    featured: bool
    owner_user_id: UUID
    can_use: bool = True


class VoiceGrantCreateRequest(BaseModel):
    grantee_user_id: UUID
    expires_at: datetime | None = None


class VoiceGrantResponse(BaseModel):
    grant_id: UUID
    voice_id: UUID
    voice_name: str
    granter_user_id: UUID
    grantee_user_id: UUID
    scope: str
    expires_at: datetime | None = None
    created_at: datetime | None = None


class BatchSubmitResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    line_count: int
    queue_position: int | None = None


class SynthesisResult(BaseModel):
    audio_url: str
    duration_sec: float | None = None
    chars_billed: int = 0


class JobRecord(BaseModel):
    job_id: UUID
    job_type: JobType
    status: JobStatus
    trace_id: str
    job_schema_version: str = JOB_SCHEMA_VERSION
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error_message: str | None = None
    owner_user_id: UUID
    queue_position: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SynthesisRequest(BaseModel):
    voice_version_id: UUID
    text: str = Field(min_length=1, max_length=5000)
    format: str = Field(default="wav", pattern="^(wav|mp3)$")
    ai_disclosure_ack: bool = True


class TrainPayload(BaseModel):
    voice_id: UUID
    voice_asset_id: UUID
    consent_id: UUID
    model_tag: str = MODEL_TAG_V2PRO
    asset_urls: list[str] = Field(default_factory=list)
    hyperparams: dict[str, Any] = Field(default_factory=dict)


class TrainRequest(BaseModel):
    voice_asset_id: UUID | None = None
    consent_id: UUID | None = None
    model_tag: str = MODEL_TAG_V2PRO


class JobSubmitResponse(BaseModel):
    job_id: UUID
    job_type: JobType
    status: JobStatus
    queue_position: int | None = None


class JobResponse(BaseModel):
    job_id: UUID
    job_type: JobType
    status: JobStatus
    queue_position: int | None = None
    error_message: str | None = None
    # synthesize
    audio_url: str | None = None
    duration_sec: float | None = None
    chars_billed: int | None = None
    # train
    voice_version_id: UUID | None = None
    checkpoint_uri: str | None = None
    model_tag: str | None = None
    # batch
    line_count: int | None = None
    succeeded_count: int | None = None
    failed_count: int | None = None
    zip_url: str | None = None


class SynthesisResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    audio_url: str | None = None
    duration_sec: float | None = None
    chars_billed: int | None = None
    queue_position: int | None = None


class VoiceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class VoiceCreateResponse(BaseModel):
    voice_id: UUID
    name: str


class ConsentCreateRequest(BaseModel):
    voice_id: UUID


class ConsentCreateResponse(BaseModel):
    consent_id: UUID
    voice_id: UUID
    status: str


class QcIssue(BaseModel):
    code: str
    message: str


class QcResult(BaseModel):
    status: str
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    issues: list[QcIssue] = Field(default_factory=list)
    ref_text: str | None = None


class AssetUploadResponse(BaseModel):
    asset_id: UUID
    voice_id: UUID
    storage_uri: str
    qc_passed: bool
    qc_result: QcResult


class AssetQcResponse(BaseModel):
    asset_id: UUID
    voice_id: UUID
    locked: bool
    qc_passed: bool
    qc_result: QcResult | None = None


class AssetConfirmResponse(BaseModel):
    asset_id: UUID
    voice_id: UUID
    locked: bool
