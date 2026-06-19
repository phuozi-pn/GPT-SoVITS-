"""Auto emotion detection API — REQ-027."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from apps.api.exceptions import raise_domain_http
from domains.emotion.service import EmotionService, EmotionServiceError
from fastapi import APIRouter, Depends
from voice_platform.emotion.schemas import (
    EmotionAnalyzeRequest,
    EmotionAnalyzeResponse,
    EmotionBatchRequest,
    EmotionBatchResponse,
)

router = APIRouter()


@router.post("/emotion/analyze", response_model=EmotionAnalyzeResponse)
def analyze(
    body: EmotionAnalyzeRequest,
    _: UUID = Depends(get_current_user_id),
) -> EmotionAnalyzeResponse:
    """Analyze a single text for auto emotion detection."""
    try:
        return EmotionService().analyze(body.text)
    except EmotionServiceError as exc:
        raise_domain_http(exc)


@router.post("/emotion/analyze-batch", response_model=EmotionBatchResponse)
def analyze_batch(
    body: EmotionBatchRequest,
    _: UUID = Depends(get_current_user_id),
) -> EmotionBatchResponse:
    """Analyze multiple text segments for emotion in one request."""
    return EmotionService().analyze_batch(body.texts)
