from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_trace_id
from apps.api.quota_http import raise_quota_http
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from domains.training.service import TrainingService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session
from domains.voices.service import VoiceService, VoiceServiceError
from domains.voices.import_service import EngineWeightsImportService, ImportServiceError
from voice_platform.job.schemas import (
    ImportEngineWeightsRequest,
    JobSubmitResponse,
    TrainRequest,
    VoiceCreateRequest,
    VoiceCreateResponse,
    VoiceSummary,
    VoiceVersionSummary,
)
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.repository import QuotaRepository

router = APIRouter()
_gateway = ComplianceGateway()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/voices", response_model=list[VoiceSummary])
def list_voices(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[VoiceSummary]:
    return VoiceService(session).list_voices(user_id)


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
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


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
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/voices/{voice_id}/train", response_model=JobSubmitResponse, status_code=202)
def create_train_job(
    voice_id: UUID,
    body: TrainRequest,
    user_id: UUID = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
) -> JobSubmitResponse:
    service = TrainingService(session)
    payload, owns, consent_ok, asset_locked, asset_qc = service.resolve_train_inputs(
        voice_id=voice_id,
        owner_user_id=user_id,
        voice_asset_id=body.voice_asset_id,
        consent_id=body.consent_id,
        model_tag=body.model_tag,
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
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc

    if payload is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "ASSET_NOT_READY", "message": "Training asset or consent missing"},
        )

    quota = QuotaRepository(session)
    try:
        quota.ensure_training_available(user_id)
    except QuotaExceededError as exc:
        raise_quota_http(exc)

    return service.submit(owner_user_id=user_id, payload=payload, trace_id=trace_id)
