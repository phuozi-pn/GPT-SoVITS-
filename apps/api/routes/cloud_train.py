from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.cloud_train.service import CloudGpuProfileError, CloudGpuProfileService
from domains.cloud_train.preview_service import CloudDatasetPreviewService, DatasetPreviewError
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter()


class CloudGpuProfileResponse(BaseModel):
    ssh_host: str
    ssh_port: int
    ssh_user: str
    auth_type: str
    has_credential: bool
    remote_engine_root: str
    remote_platform_root: str
    remote_work_dir: str
    last_tested_at: str | None = None
    last_test_ok: bool | None = None


class CloudGpuProfileSaveRequest(BaseModel):
    ssh_host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="root", min_length=1, max_length=64)
    password: str = Field(default="", max_length=512)
    remote_engine_root: str = Field(default="/root/autodl-tmp/GPT-SoVITS", max_length=512)
    remote_platform_root: str = Field(default="/root/autodl-tmp/GPT", max_length=512)
    remote_work_dir: str = Field(default="/root/autodl-tmp/cloud_train_jobs", max_length=512)


class CloudGpuProfileTestRequest(BaseModel):
    ssh_host: str | None = None
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    ssh_user: str | None = None
    password: str | None = None
    remote_engine_root: str | None = None
    remote_platform_root: str | None = None


class CloudGpuTestResponse(BaseModel):
    ok: bool
    message: str
    checks: list[dict] = Field(default_factory=list)


class DatasetPreviewSegment(BaseModel):
    index: int
    name: str
    duration_sec: float
    text: str
    audio_url: str
    text_original: str | None = None
    emotion: str | None = None
    emotion_label: str | None = None
    emotion_strength: float | None = None
    notes: str | None = None


class DatasetPreviewRequest(BaseModel):
    asset_id: UUID
    use_asr: bool | None = None
    use_llm_enrich: bool | None = None


class DatasetPreviewResponse(BaseModel):
    asset_id: str
    source_duration_sec: float
    mode: str
    segment_count: int
    use_asr: bool
    segments: list[DatasetPreviewSegment]
    infer_ref_text: str
    enrich_mode: str = "off"


@router.get("/cloud-gpu/profile", response_model=CloudGpuProfileResponse | None)
def get_cloud_gpu_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CloudGpuProfileResponse | None:
    data = CloudGpuProfileService(session).get_profile(user_id)
    return CloudGpuProfileResponse.model_validate(data) if data else None


@router.put("/cloud-gpu/profile", response_model=CloudGpuProfileResponse)
def save_cloud_gpu_profile(
    body: CloudGpuProfileSaveRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CloudGpuProfileResponse:
    try:
        data = CloudGpuProfileService(session).save_profile(
            user_id=user_id,
            ssh_host=body.ssh_host,
            ssh_port=body.ssh_port,
            ssh_user=body.ssh_user,
            password=body.password,
            remote_engine_root=body.remote_engine_root,
            remote_platform_root=body.remote_platform_root,
            remote_work_dir=body.remote_work_dir,
        )
        return CloudGpuProfileResponse.model_validate(data)
    except CloudGpuProfileError as exc:
        raise_domain_http(exc)


@router.post("/cloud-gpu/profile/test", response_model=CloudGpuTestResponse)
def test_cloud_gpu_profile(
    body: CloudGpuProfileTestRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> CloudGpuTestResponse:
    try:
        result = CloudGpuProfileService(session).test_connection(
            user_id=user_id,
            ssh_host=body.ssh_host,
            ssh_port=body.ssh_port,
            ssh_user=body.ssh_user,
            password=body.password,
            remote_engine_root=body.remote_engine_root,
            remote_platform_root=body.remote_platform_root,
        )
        return CloudGpuTestResponse.model_validate(result)
    except CloudGpuProfileError as exc:
        raise_domain_http(exc)


@router.post("/cloud-gpu/dataset-preview", response_model=DatasetPreviewResponse)
def preview_cloud_dataset(
    body: DatasetPreviewRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> DatasetPreviewResponse:
    try:
        data = CloudDatasetPreviewService(session).preview(
            owner_user_id=user_id,
            asset_id=body.asset_id,
            use_asr=body.use_asr,
            use_llm_enrich=body.use_llm_enrich,
        )
        return DatasetPreviewResponse.model_validate(data)
    except DatasetPreviewError as exc:
        raise_domain_http(exc)


@router.delete("/cloud-gpu/profile", status_code=204)
def delete_cloud_gpu_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> None:
    try:
        CloudGpuProfileService(session).delete_profile(user_id)
    except CloudGpuProfileError as exc:
        raise_domain_http(exc)
