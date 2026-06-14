from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.assets.qc import AssetQcError
from domains.assets.service import AssetService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session
from voice_platform.job.schemas import AssetConfirmResponse, AssetQcResponse, AssetUploadResponse

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def _raise_asset_error(exc: AssetQcError) -> None:
    status = 403 if exc.code in {"FORBIDDEN", "CONSENT_REQUIRED"} else 400
    if exc.code.startswith("QC_"):
        status = 422
    raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/voices/assets", response_model=AssetUploadResponse, status_code=201)
async def upload_voice_asset(
    voice_id: UUID = Form(...),
    ref_text: str | None = Form(default=None),
    audio_file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AssetUploadResponse:
    data = await audio_file.read()
    filename = audio_file.filename or "upload.wav"
    service = AssetService(session)
    try:
        return service.upload(
            owner_user_id=user_id,
            voice_id=voice_id,
            filename=filename,
            data=data,
            ref_text=ref_text,
        )
    except AssetQcError as exc:
        _raise_asset_error(exc)


@router.get("/voices/assets/{asset_id}/qc", response_model=AssetQcResponse)
def get_asset_qc(
    asset_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AssetQcResponse:
    service = AssetService(session)
    try:
        return service.get_qc(owner_user_id=user_id, asset_id=asset_id)
    except AssetQcError as exc:
        _raise_asset_error(exc)


@router.post("/voices/assets/{asset_id}/confirm", response_model=AssetConfirmResponse)
def confirm_voice_asset(
    asset_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AssetConfirmResponse:
    service = AssetService(session)
    try:
        return service.confirm(owner_user_id=user_id, asset_id=asset_id)
    except AssetQcError as exc:
        _raise_asset_error(exc)
