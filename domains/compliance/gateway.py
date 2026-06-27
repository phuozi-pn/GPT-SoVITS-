from __future__ import annotations

import re
from collections.abc import Callable
from uuid import UUID

from domains.compliance.wordlist import find_sensitive_word
from voice_platform.config import get_settings
from voice_platform.job.schemas import InferPayload, InferSegment, SynthesisRequest


class ComplianceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


_PUNCT_ONLY = re.compile(r"^[\s\W]+$", re.UNICODE)


class ComplianceGateway:
    def __init__(self, *, wordlist_path: str | None = None) -> None:
        settings = get_settings()
        self._wordlist_path = wordlist_path or settings.compliance_wordlist_path or None

    def validate_synthesis(
        self,
        *,
        user_id: UUID,
        voice_version_id: UUID | None = None,
        text: str | None = None,
        has_voice_access: bool = False,
        ai_disclosure_ack: bool = True,
        temperature: float | None = None,
        speed_factor: float | None = None,
        top_p: float | None = None,
        emotion: str | None = None,
        emotion_strength: float = 0.5,
        segments: list[InferSegment] | None = None,
        voice_access_checker: Callable[[UUID], bool] | None = None,
        project_type: str | None = None,
    ) -> InferPayload:
        if not ai_disclosure_ack:
            raise ComplianceError("AI_DISCLOSURE_REQUIRED", "AI disclosure required", 403)

        if segments:
            cleaned_segments: list[InferSegment] = []
            for seg in segments:
                if voice_access_checker and not voice_access_checker(seg.voice_version_id):
                    raise ComplianceError("VOICE_NOT_GRANTED", "Voice version not accessible", 403)
                cleaned = self._validate_text(seg.text, max_len=2000)
                cleaned_segments.append(
                    InferSegment(
                        voice_version_id=seg.voice_version_id,
                        text=cleaned,
                        speed_factor=seg.speed_factor,
                        temperature=seg.temperature,
                        top_p=seg.top_p,
                        pitch_factor=seg.pitch_factor,
                        emotion=seg.emotion,
                        emotion_strength=seg.emotion_strength,
                        pause_duration=seg.pause_duration,
                    )
                )
            return InferPayload(
                segments=cleaned_segments,
                temperature=temperature,
                speed_factor=speed_factor,
                top_p=top_p,
                emotion=emotion,
                emotion_strength=emotion_strength,
                project_type=project_type,
            )

        if not has_voice_access:
            raise ComplianceError("VOICE_NOT_GRANTED", "Voice version not accessible", 403)
        cleaned = self._validate_text(text or "")
        return InferPayload(
            voice_version_id=voice_version_id,
            text=cleaned,
            temperature=temperature,
            speed_factor=speed_factor,
            top_p=top_p,
            emotion=emotion,
            emotion_strength=emotion_strength,
            project_type=project_type,
        )

    def validate_synthesis_request(
        self,
        *,
        user_id: UUID,
        body: SynthesisRequest,
        voice_access_checker: Callable[[UUID], bool],
    ) -> InferPayload:
        segments = None
        if body.segments:
            segments = [
                InferSegment(
                    voice_version_id=s.voice_version_id,
                    text=s.text,
                    speed_factor=s.speed_factor,
                    temperature=s.temperature,
                    top_p=s.top_p,
                    pitch_factor=s.pitch_factor,
                    emotion=s.emotion,
                    emotion_strength=s.emotion_strength,
                    pause_duration=s.pause_duration,
                )
                for s in body.segments
            ]
        return self.validate_synthesis(
            user_id=user_id,
            voice_version_id=body.voice_version_id,
            text=body.text,
            has_voice_access=bool(body.voice_version_id and voice_access_checker(body.voice_version_id)),
            ai_disclosure_ack=body.ai_disclosure_ack,
            temperature=body.temperature,
            speed_factor=body.speed_factor,
            top_p=body.top_p,
            emotion=body.emotion,
            emotion_strength=body.emotion_strength,
            segments=segments,
            voice_access_checker=voice_access_checker,
            project_type=body.project_type,
        )

    def validate_batch_line_text(self, text: str) -> str:
        """Basic + sensitive check for a single CSV line (batch worker)."""
        return self._validate_text(text)

    def precheck_texts(
        self,
        texts: list[str],
        *,
        segmented: bool = False,
    ) -> list[dict[str, str | int | None]]:
        """Non-blocking compliance scan for UI hints before synthesis."""
        max_len = 2000 if segmented else 5000
        issues: list[dict[str, str | int | None]] = []
        for index, raw in enumerate(texts):
            text = (raw or "").strip()
            if not text or _PUNCT_ONLY.match(text):
                issues.append(
                    {
                        "code": "INVALID_TEXT",
                        "message": "台词为空或只有标点",
                        "segment_index": index,
                    }
                )
                continue
            if len(text) > max_len:
                issues.append(
                    {
                        "code": "TEXT_TOO_LONG",
                        "message": f"超过 {max_len} 字（当前 {len(text)} 字）",
                        "segment_index": index,
                    }
                )
            hit = find_sensitive_word(text, path=self._wordlist_path)
            if hit:
                issues.append(
                    {
                        "code": "SENSITIVE_WORD",
                        "message": f"含敏感词「{hit}」",
                        "segment_index": index,
                    }
                )
        return issues

    def _validate_text(self, text: str, *, max_len: int = 5000) -> str:
        cleaned = text.strip()
        if not cleaned or _PUNCT_ONLY.match(cleaned):
            raise ComplianceError("INVALID_TEXT", "Text is empty or punctuation only", 400)
        if len(cleaned) > max_len:
            raise ComplianceError("TEXT_TOO_LONG", f"Text exceeds {max_len} characters", 400)
        hit = find_sensitive_word(cleaned, path=self._wordlist_path)
        if hit:
            raise ComplianceError("SENSITIVE_WORD", f"Sensitive word blocked: {hit}", 400)
        return cleaned

    def validate_train(
        self,
        *,
        user_id: UUID,
        voice_id: UUID,
        owns_voice: bool,
        consent_approved: bool,
        asset_locked: bool,
        asset_qc_passed: bool,
        model_tag: str,
    ) -> None:
        if not owns_voice:
            raise ComplianceError("FORBIDDEN", "Voice not accessible", 403)
        if not consent_approved:
            raise ComplianceError("CONSENT_REQUIRED", "Approved consent required", 403)
        if not asset_locked or not asset_qc_passed:
            raise ComplianceError("ASSET_NOT_READY", "Training asset not locked or QC failed", 403)
        if model_tag != "gsv-v2pro-20250606":
            raise ComplianceError("INVALID_MODEL_TAG", f"Unsupported model_tag: {model_tag}", 400)
