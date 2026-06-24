from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_trace_id
from apps.api.exceptions import raise_domain_http
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from domains.kyc.service import KycService, KycServiceError
from domains.quota.service import QuotaService, QuotaServiceError
from domains.training.service import TrainingService
from domains.training.validate import TrainingServiceError, validate_train_backend
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from domains.voices.service import VoiceService, VoiceServiceError
from domains.voices.import_service import EngineWeightsImportService, ImportServiceError
from voice_platform.job.schemas import (
    ImportEngineWeightsRequest,
    JobSubmitResponse,
    TrainRequest,
    VoiceCreateRequest,
    VoiceCreateResponse,
    VoiceSummary,
    VoiceUpdateRequest,
    VoiceVersionSummary,
    VoiceVersionUpdateRequest,
)

router = APIRouter()
_gateway = ComplianceGateway()


@router.get("/voices", response_model=list[VoiceSummary])
def list_voices(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
    detail: bool = False,
) -> list[VoiceSummary]:
    return VoiceService(session).list_voices(user_id, detail=detail)


@router.patch("/voices/{voice_id}", response_model=VoiceSummary)
def update_voice(
    voice_id: UUID,
    body: VoiceUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceSummary:
    service = VoiceService(session)
    try:
        return service.update_voice_name(voice_id=voice_id, owner_user_id=user_id, name=body.name)
    except VoiceServiceError as exc:
        raise_domain_http(exc)


@router.delete("/voices/{voice_id}", status_code=204)
def delete_voice(
    voice_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> None:
    service = VoiceService(session)
    try:
        service.delete_voice(voice_id=voice_id, owner_user_id=user_id)
    except VoiceServiceError as exc:
        raise_domain_http(exc)


@router.patch("/voice-versions/{voice_version_id}", response_model=VoiceVersionSummary)
def update_voice_version(
    voice_version_id: UUID,
    body: VoiceVersionUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceVersionSummary:
    service = VoiceService(session)
    try:
        return service.update_version(
            voice_version_id=voice_version_id,
            owner_user_id=user_id,
            label=body.label,
            ref_text=body.ref_text,
        )
    except VoiceServiceError as exc:
        raise_domain_http(exc)


@router.delete("/voice-versions/{voice_version_id}", status_code=204)
def delete_voice_version(
    voice_version_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> None:
    service = VoiceService(session)
    try:
        service.delete_version(voice_version_id=voice_version_id, owner_user_id=user_id)
    except VoiceServiceError as exc:
        raise_domain_http(exc)


@router.get("/voice-versions", response_model=list[VoiceVersionSummary])
def list_voice_versions(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[VoiceVersionSummary]:
    return VoiceService(session).list_versions(user_id)


@router.post("/voices/import-weights", response_model=VoiceVersionSummary, status_code=201)
def import_engine_weights(
    body: ImportEngineWeightsRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceVersionSummary:
    try:
        return EngineWeightsImportService(session).import_weights(owner_user_id=user_id, body=body)
    except ImportServiceError as exc:
        raise_domain_http(exc)


@router.post("/voices/import-weights/upload", response_model=VoiceVersionSummary, status_code=201)
async def import_engine_weights_upload(
    gpt_weights: UploadFile = File(...),
    sovits_weights: UploadFile = File(...),
    ref_audio: UploadFile = File(...),
    voice_name: str = Form(default="导入音色"),
    ref_text: str = Form(...),
    voice_id: UUID | None = Form(default=None),
    label: str = Form(default=""),
    consent_id: UUID | None = Form(default=None),
    voice_asset_id: UUID | None = Form(default=None),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceVersionSummary:
    try:
        return EngineWeightsImportService(session).import_uploaded_files(
            owner_user_id=user_id,
            voice_name=voice_name,
            ref_text=ref_text,
            gpt_bytes=await gpt_weights.read(),
            sovits_bytes=await sovits_weights.read(),
            ref_bytes=await ref_audio.read(),
            voice_id=voice_id,
            label=label,
            consent_id=consent_id,
            voice_asset_id=voice_asset_id,
        )
    except ImportServiceError as exc:
        raise_domain_http(exc)


@router.post("/voices", response_model=VoiceCreateResponse, status_code=201)
def create_voice(
    body: VoiceCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> VoiceCreateResponse:
    service = VoiceService(session)
    try:
        return service.create(owner_user_id=user_id, name=body.name)
    except VoiceServiceError as exc:
        raise_domain_http(exc)


@router.post("/voices/{voice_id}/train", response_model=JobSubmitResponse, status_code=202)
def create_train_job(
    voice_id: UUID,
    body: TrainRequest,
    user_id: UUID = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
) -> JobSubmitResponse:
    try:
        KycService(session).ensure_verified_for_train(user_id)
    except KycServiceError as exc:
        raise_domain_http(exc)

    try:
        validate_train_backend(body.train_backend, session=session, user_id=user_id)
    except TrainingServiceError as exc:
        raise_domain_http(exc)

    service = TrainingService(session)
    payload, owns, consent_ok, asset_locked, asset_qc = service.resolve_train_inputs(
        voice_id=voice_id,
        owner_user_id=user_id,
        voice_asset_id=body.voice_asset_id,
        consent_id=body.consent_id,
        model_tag=body.model_tag,
        train_backend=body.train_backend,
        cloud_local_dataset_prep=body.cloud_local_dataset_prep,
        cloud_use_asr=body.cloud_use_asr,
    )
    try:
        _gateway.validate_train(
            user_id=user_id,
            voice_id=voice_id,
            owns_voice=owns,
            consent_approved=consent_ok,
            asset_locked=asset_locked,
            asset_qc_passed=asset_qc,
            model_tag=body.model_tag,
        )
    except ComplianceError as exc:
        raise_domain_http(exc)

    if payload is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "ASSET_NOT_READY", "message": "Training asset or consent missing"},
        )

    try:
        QuotaService(session).ensure_training_available(user_id)
    except QuotaServiceError as exc:
        raise_domain_http(exc)

    return service.submit(owner_user_id=user_id, payload=payload, trace_id=trace_id)
