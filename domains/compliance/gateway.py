from __future__ import annotations

import re
from uuid import UUID

from voice_platform.job.schemas import InferPayload


class ComplianceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


_PUNCT_ONLY = re.compile(r"^[\s\W]+$", re.UNICODE)

# W1 stub — replace with module G integration
_DEFAULT_BLOCKLIST = {"测试敏感词"}


class ComplianceGateway:
    def validate_synthesis(
        self,
        *,
        user_id: UUID,
        voice_version_id: UUID,
        text: str,
        has_voice_access: bool,
        ai_disclosure_ack: bool = True,
    ) -> InferPayload:
        if not ai_disclosure_ack:
            raise ComplianceError("AI_DISCLOSURE_REQUIRED", "AI disclosure required", 403)
        if not has_voice_access:
            raise ComplianceError("VOICE_NOT_GRANTED", "Voice version not accessible", 403)
        cleaned = text.strip()
        if not cleaned or _PUNCT_ONLY.match(cleaned):
            raise ComplianceError("INVALID_TEXT", "Text is empty or punctuation only", 400)
        if len(cleaned) > 5000:
            raise ComplianceError("TEXT_TOO_LONG", "Text exceeds 5000 characters", 400)
        for word in _DEFAULT_BLOCKLIST:
            if word in cleaned:
                raise ComplianceError("SENSITIVE_WORD", f"Sensitive word blocked: {word}", 400)
        return InferPayload(voice_version_id=voice_version_id, text=cleaned)

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
