from __future__ import annotations

import logging
from typing import Any

import httpx

from voice_platform.config import get_settings
from voice_platform.job.schemas import JobRecord

logger = logging.getLogger(__name__)


def _build_message(record: JobRecord) -> str:
    lines = [
        "[Voice Platform] Job failed",
        f"job_id: {record.job_id}",
        f"job_type: {record.job_type.value}",
        f"trace_id: {record.trace_id}",
        f"owner: {record.owner_user_id}",
        f"error: {(record.error_message or '')[:500]}",
    ]
    return "\n".join(lines)


def _feishu_payload(text: str) -> dict[str, Any]:
    return {"msg_type": "text", "content": {"text": text}}


def maybe_alert_job_failed(record: JobRecord) -> None:
    """Send webhook alert when configured (Feishu/Lark text or generic JSON)."""
    settings = get_settings()
    if not settings.alert_on_job_failure:
        return
    url = (settings.alert_webhook_url or "").strip()
    if not url:
        return

    text = _build_message(record)
    payload: dict[str, Any]
    if settings.alert_webhook_format == "feishu":
        payload = _feishu_payload(text)
    elif settings.alert_webhook_format == "generic":
        payload = {
            "event": "job_failed",
            "job_id": str(record.job_id),
            "job_type": record.job_type.value,
            "trace_id": record.trace_id,
            "owner_user_id": str(record.owner_user_id),
            "error_message": record.error_message,
        }
    else:
        payload = _feishu_payload(text)

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "alert webhook failed status=%s body=%s trace_id=%s job_id=%s",
                    resp.status_code,
                    resp.text[:200],
                    record.trace_id,
                    record.job_id,
                )
            else:
                logger.info(
                    "alert sent job_id=%s trace_id=%s",
                    record.job_id,
                    record.trace_id,
                )
    except Exception:
        logger.exception(
            "alert webhook error job_id=%s trace_id=%s",
            record.job_id,
            record.trace_id,
        )
