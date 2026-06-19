"""Audio fingerprint registration & search API — REQ-025."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.fingerprint.service import FingerprintService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from voice_platform.fingerprint.schemas import (
    FingerprintEnrollRequest,
    FingerprintEnrollResponse,
    FingerprintSearchResponse,
    FingerprintStatusResponse,
)

router = APIRouter()

# Module-level singleton service (in-memory store shared across requests)
_service = FingerprintService()


@router.post("/fingerprint/enroll", response_model=FingerprintEnrollResponse)
def enroll(
    body: FingerprintEnrollRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> FingerprintEnrollResponse:
    """Register an audio fingerprint from a WAV file for later search."""
    return _service.enroll(
        user_id=body.user_id or user_id,
        job_id=body.job_id,
        voice_id=body.voice_id,
        storage_url=body.storage_url,
    )


@router.post("/fingerprint/enroll-audio")
def enroll_audio(
    file: UploadFile = File(...),
    job_id: str = Form(...),
    user_id: UUID = Depends(get_current_user_id),
) -> FingerprintEnrollResponse:
    """Upload a WAV file and register its fingerprint directly."""
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": "Only WAV files are accepted"})

    try:
        wav_bytes = file.file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"code": "READ_ERROR", "message": str(exc)}) from exc

    return _service.enroll_audio(
        wav_bytes=wav_bytes,
        job_id=UUID(job_id),
        user_id=user_id,
    )


@router.post("/fingerprint/search", response_model=FingerprintSearchResponse)
def search(
    file: UploadFile = File(...),
    threshold: float = Form(0.05),
    max_results: int = Form(10),
    _user_id: UUID = Depends(get_current_user_id),
) -> FingerprintSearchResponse:
    """Search for matching fingerprints by uploading a WAV file."""
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": "Only WAV files are accepted"})

    try:
        wav_bytes = file.file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"code": "READ_ERROR", "message": str(exc)}) from exc

    return _service.search(
        wav_bytes=wav_bytes,
        threshold=threshold,
        max_results=max_results,
    )


@router.get("/fingerprint/status", response_model=FingerprintStatusResponse)
def status(_user_id: UUID = Depends(get_current_user_id)) -> FingerprintStatusResponse:
    """Get fingerprint store status."""
    return _service.status()
