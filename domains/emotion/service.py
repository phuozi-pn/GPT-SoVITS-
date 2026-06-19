"""REQ-027 Auto emotion detection domain service."""

from __future__ import annotations

from voice_platform.emotion.analyzer import analyze_emotion, emotion_label
from voice_platform.emotion.schemas import (
    EmotionAnalyzeResponse,
    EmotionBatchItem,
    EmotionBatchResponse,
)


class EmotionServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class EmotionService:
    """Text emotion analysis use case — wraps keyword-based analyzer."""

    def analyze(self, text: str) -> EmotionAnalyzeResponse:
        """Analyze a single text for auto emotion detection."""
        try:
            emotion, strength = analyze_emotion(text)
        except Exception as exc:
            raise EmotionServiceError(
                "EMOTION_ANALYSIS_FAILED",
                str(exc),
                500,
            ) from exc

        preview = text[:120] if len(text) > 120 else text
        return EmotionAnalyzeResponse(
            emotion=emotion,
            emotion_label=emotion_label(emotion),
            strength=round(strength, 3),
            text_preview=preview,
        )

    def analyze_batch(self, texts: list[str]) -> EmotionBatchResponse:
        """Analyze multiple text segments for emotion in one call."""
        results: list[EmotionBatchItem] = []
        for i, text in enumerate(texts):
            try:
                emotion, strength = analyze_emotion(text)
            except Exception:
                emotion, strength = "neutral", 0.1
            results.append(
                EmotionBatchItem(
                    index=i,
                    emotion=emotion,
                    emotion_label=emotion_label(emotion),
                    strength=round(strength, 3),
                )
            )
        return EmotionBatchResponse(results=results)
