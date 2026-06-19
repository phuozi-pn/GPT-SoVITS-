from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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


class InferSegment(BaseModel):
    voice_version_id: UUID
    text: str = Field(min_length=1, max_length=2000)
    speed_factor: float | None = Field(default=None, ge=0.5, le=2.0)
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    top_p: float | None = Field(default=None, ge=0.1, le=1.0)
    pitch_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    emotion: str | None = Field(default=None, max_length=32)
    emotion_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    pause_duration: float = Field(default=0.0, ge=0.0, le=5.0, description="Inter-segment pause in seconds")


class InferPayload(BaseModel):
    voice_version_id: UUID | None = None
    text: str | None = None
    format: str = "wav"
    sample_rate: int = 32000
    catalog_id: UUID | None = None
    skip_quota: bool = False
    project_type: str | None = None
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    speed_factor: float | None = Field(default=None, ge=0.5, le=2.0)
    top_p: float | None = Field(default=None, ge=0.1, le=1.0)
    emotion: str | None = Field(default=None, max_length=32)
    emotion_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    segments: list[InferSegment] | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> InferPayload:
        if self.segments:
            if not self.segments:
                raise ValueError("segments must not be empty")
            return self
        if not self.voice_version_id or not self.text:
            raise ValueError("voice_version_id and text are required for single synthesis")
        return self

    def billed_char_count(self) -> int:
        if self.segments:
            return sum(len(s.text) for s in self.segments)
        return len(self.text or "")


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
    granted: bool = False
    created_at: datetime | None = None


class VoiceSummary(BaseModel):
    voice_id: UUID
    name: str
    version_count: int = 0
    latest_version_id: UUID | None = None
    versions: list["VoiceVersionManageSummary"] | None = None
    assets: list["VoiceAssetManageSummary"] | None = None
    consents: list["VoiceConsentManageSummary"] | None = None


class VoiceUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class VoiceVersionUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=128)
    ref_text: str | None = Field(default=None, max_length=4000)


class VoiceVersionManageSummary(VoiceVersionSummary):
    catalog_id: UUID | None = None
    catalog_status: str | None = None
    catalog_title: str | None = None
    can_unpublish: bool = False
    can_delete: bool = True
    delete_block_reason: str | None = None


class VoiceAssetManageSummary(BaseModel):
    asset_id: UUID
    voice_id: UUID
    storage_uri: str
    locked: bool = False
    qc_passed: bool = False
    qc_status: str | None = None
    duration_sec: float | None = None
    created_at: datetime | None = None


class VoiceConsentManageSummary(BaseModel):
    consent_id: UUID
    voice_id: UUID
    status: str
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None


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
    demo_text: str = Field(default="", max_length=500)
    license_type: str = Field(default="personal_non_commercial")
    price_cents: int = Field(default=0, ge=0, le=10_000_000)
    billing_unit: str = Field(default="per_1k_chars")
    included_chars: int = Field(default=50_000, ge=0, le=50_000_000)
    prohibited_domains: list[str] = Field(default_factory=list, max_length=10)


class CatalogLicensePolicyRequest(BaseModel):
    license_type: str
    price_cents: int = Field(ge=0, le=10_000_000)
    billing_unit: str = Field(default="per_1k_chars")
    included_chars: int = Field(default=50_000, ge=0, le=50_000_000)
    prohibited_domains: list[str] = Field(default_factory=list, max_length=10)


class CatalogEntryResponse(BaseModel):
    catalog_id: UUID
    voice_version_id: UUID
    voice_id: UUID
    voice_name: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    featured: bool
    status: str = "published"
    demo_text: str = ""
    demo_audio_url: str | None = None
    demo_job_id: UUID | None = None
    owner_user_id: UUID
    can_use: bool = True
    license_type: str = "personal_non_commercial"
    price_cents: int = 0
    billing_unit: str = "per_1k_chars"
    included_chars: int = 50000
    prohibited_domains: list[str] = Field(default_factory=list)
    policy_version: int = 1
    purchased: bool = False


class CreatorProfileResponse(BaseModel):
    user_id: UUID
    display_name: str
    bio: str = ""
    published_count: int
    voices: list[CatalogEntryResponse] = Field(default_factory=list)


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


class AuthorizationResponse(BaseModel):
    authorization_id: UUID
    catalog_id: UUID
    voice_version_id: UUID
    voice_id: UUID
    voice_title: str
    seller_user_id: UUID
    buyer_user_id: UUID
    license_type: str
    billing_unit: str
    char_quota_total: int
    char_quota_used: int
    char_quota_remaining: int
    price_paid_cents: int
    payment_ref: str
    status: str
    expires_at: datetime | None = None
    created_at: datetime | None = None


class PaymentOrderResponse(BaseModel):
    order_id: UUID
    authorization_id: UUID | None = None
    catalog_id: UUID
    buyer_user_id: UUID
    seller_user_id: UUID
    amount_cents: int
    currency: str
    status: str
    provider: str
    provider_ref: str
    paid_at: datetime | None = None
    created_at: datetime | None = None


class AuthorizationCertificateResponse(BaseModel):
    authorization_id: UUID
    platform: str = "Voice Studio"
    seller_user_id: UUID
    buyer_user_id: UUID
    voice_version_id: UUID
    catalog_id: UUID
    voice_title: str
    license_type: str
    char_quota_total: int
    char_quota_used: int
    status: str
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    signature: str


class AuthorizationVerifyResponse(BaseModel):
    authorization_id: UUID
    status: str
    valid: bool
    voice_title: str
    license_type: str
    message: str


class ComplaintCreateRequest(BaseModel):
    catalog_id: UUID | None = None
    voice_version_id: UUID | None = None
    target_url: str = Field(default="", max_length=2000)
    description: str = Field(min_length=10, max_length=5000)
    evidence_urls: list[str] = Field(default_factory=list, max_length=5)


class ComplaintResponse(BaseModel):
    complaint_id: UUID
    catalog_id: UUID | None = None
    voice_version_id: UUID | None = None
    reporter_user_id: UUID
    target_url: str
    description: str
    evidence_urls: list[str] = Field(default_factory=list)
    status: str
    resolution_note: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class BatchLineStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BatchLineResponse(BaseModel):
    line_index: int
    role: str
    text: str
    voice_version_id: UUID
    status: BatchLineStatus
    audio_url: str | None = None
    duration_sec: float | None = None
    export_compliant: bool = False
    label_type: str | None = None
    labeled_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class BatchLinesResponse(BaseModel):
    job_id: UUID
    lines: list[BatchLineResponse]
    total: int
    succeeded: int
    failed: int
    queued: int
    running: int


class BatchLineRetryRequest(BaseModel):
    """失败行重试请求 — 指定要重试的行索引列表。"""
    line_indices: list[int] = Field(min_length=1, max_length=100)


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


class SynthesisSegmentRequest(BaseModel):
    voice_version_id: UUID
    text: str = Field(min_length=1, max_length=2000)
    speed_factor: float | None = Field(default=None, ge=0.5, le=2.0)
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    top_p: float | None = Field(default=None, ge=0.1, le=1.0)
    pitch_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    emotion: str | None = Field(default=None, max_length=32)
    emotion_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    pause_duration: float = Field(default=0.0, ge=0.0, le=5.0)


class SynthesisRequest(BaseModel):
    voice_version_id: UUID | None = None
    text: str | None = Field(default=None, min_length=1, max_length=5000)
    format: str = Field(default="wav", pattern="^(wav|mp3)$")
    ai_disclosure_ack: bool = True
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    speed_factor: float | None = Field(default=None, ge=0.5, le=2.0)
    top_p: float | None = Field(default=None, ge=0.1, le=1.0)
    emotion: str | None = Field(default=None, max_length=32)
    emotion_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    segments: list[SynthesisSegmentRequest] | None = Field(default=None, min_length=1, max_length=50)
    project_type: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_mode(self) -> SynthesisRequest:
        if self.segments:
            return self
        if not self.voice_version_id or not self.text:
            raise ValueError("voice_version_id and text are required when segments is omitted")
        return self


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
    trace_id: str | None = None
    owner_user_id: UUID | None = None
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


class QualityReportResponse(BaseModel):
    voice_version_id: UUID
    similarity_score: float
    quality_pass: bool
    threshold: float
    eval_sentence: str
    ref_audio_url: str | None = None
    synth_audio_url: str | None = None
    method: str
    ab_vote_count: int = 0
    ref_pick_rate: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AbTrialResponse(BaseModel):
    voice_version_id: UUID
    audio_a_url: str
    audio_b_url: str
    slot_a_kind: str
    slot_b_kind: str
    instruction: str = "盲听：哪一段更像原始训练素材？"


class AbVoteRequest(BaseModel):
    pick_slot: str = Field(pattern="^(a|b)$")
    slot_a_kind: str = Field(pattern="^(ref|synth)$")
    slot_b_kind: str = Field(pattern="^(ref|synth)$")
    score: int | None = Field(default=None, ge=1, le=5)


class AbVoteResponse(BaseModel):
    vote_id: UUID
    picked_kind: str
    correct: bool
    message: str
