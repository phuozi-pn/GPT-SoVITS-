"""Digital watermark detection API — REQ-019."""
from __future__ import annotations

from domains.watermark.service import WatermarkService
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()


@router.post("/watermark/detect")
async def detect_watermark(file: UploadFile = File(...)):
    """Detect embedded digital watermark in an audio file.

    Upload a WAV file and get back the watermark metadata if present.
    Returns the embedded user_id, voice_id, job_id, and timestamp.
    """
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files are supported for watermark detection")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    payload = WatermarkService().detect(content)
    if payload is None:
        return {
            "watermark_detected": False,
            "message": "No digital watermark found in this audio file.",
        }

    return {
        "watermark_detected": True,
        "user_id": payload.user_id,
        "voice_id": payload.voice_id,
        "job_id": payload.job_id,
        "timestamp": payload.timestamp,
    }
