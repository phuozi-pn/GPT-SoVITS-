from __future__ import annotations

import logging
from pathlib import Path

from domains.assets.errors import AssetQcError
from voice_platform.asr.service import AssetAsrService
from voice_platform.config import Settings, get_settings
from voice_platform.job.schemas import QcIssue

logger = logging.getLogger(__name__)


def resolve_upload_ref_text(
    wav_path: Path,
    user_ref: str | None,
    *,
    settings: Settings | None = None,
) -> tuple[str | None, bool, str | None, list[QcIssue]]:
    """Return (ref_text, auto, provider, extra_qc_issues)."""
    settings = settings or get_settings()
    manual = (user_ref or "").strip()
    if manual:
        return manual, False, None, []

    if not settings.asset_asr_enabled:
        return None, False, None, [
            QcIssue(
                code="REF_TEXT_REQUIRED",
                message="请填写参考文本，或开启 ASR_ENABLED 自动识别",
            )
        ]

    service = AssetAsrService(settings)
    if not service.is_available():
        return None, False, None, [
            QcIssue(
                code="ASR_UNAVAILABLE",
                message=(
                    "自动识别未就绪：pip install 'voice-platform[asr]'，"
                    "或设置 ASR_MOCK=true（仅开发）"
                ),
            )
        ]

    try:
        result = service.transcribe_clip(wav_path)
    except Exception as exc:
        logger.exception("asr failed for %s", wav_path)
        return None, False, None, [
            QcIssue(code="ASR_FAILED", message=f"自动识别失败：{exc}")
        ]

    text = result.text.strip()
    if not text:
        return None, False, result.provider, [
            QcIssue(code="ASR_FAILED", message="自动识别结果为空，请手动填写参考文本")
        ]

    if len(text) > 4000:
        raise AssetQcError("TEXT_TOO_LONG", "ASR transcript exceeds 4000 characters", 400)

    return text, True, result.provider, []
