from __future__ import annotations

from pydantic import BaseModel, Field


class EmotionAnalyzeRequest(BaseModel):
    """Request body for auto emotion analysis."""

    text: str = Field(min_length=1, max_length=5000, description="Text to analyze for emotion")


class EmotionAnalyzeResponse(BaseModel):
    """Result of auto emotion analysis."""

    emotion: str = Field(description="Detected emotion label")
    emotion_label: str = Field(description="Human-readable emotion label in Chinese")
    strength: float = Field(ge=0.0, le=1.0, description="Confidence / strength of the detected emotion")
    text_preview: str = Field(max_length=120, description="First 120 chars of analyzed text")


class EmotionBatchRequest(BaseModel):
    """Analyze multiple text segments at once."""

    texts: list[str] = Field(min_length=1, max_length=100, description="Text segments to analyze")


class EmotionBatchItem(BaseModel):
    index: int
    emotion: str
    emotion_label: str
    strength: float


class EmotionBatchResponse(BaseModel):
    results: list[EmotionBatchItem]
