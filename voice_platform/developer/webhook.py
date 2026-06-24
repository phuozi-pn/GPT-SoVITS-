"""Dispatch Open API job completion webhooks (REQ-030)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.developer.repository import ApiKeyRepository
from voice_platform.webhook.delivery import enqueue_webhook_delivery, process_due_webhook_retries

logger = logging.getLogger(__name__)


def dispatch_open_api_job_webhook(
    session: Session,
    *,
    api_key_id: UUID,
    job_id: UUID,
    status: str,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    row = ApiKeyRepository(session).get(api_key_id)
    if not row or not row.webhook_url:
        return

    payload = {
        "event": "job.finished",
        "job_id": str(job_id),
        "status": status,
        "result": result or {},
        "error_message": error_message,
    }
    delivery = enqueue_webhook_delivery(
        session,
        channel="open_api_job",
        target_url=row.webhook_url,
        payload=payload,
        signature_secret=(row.webhook_secret or "").strip() or None,
    )
    if delivery.status != "delivered":
        logger.warning(
            "open api webhook pending retry status=%s job_id=%s url=%s attempts=%s",
            delivery.status,
            job_id,
            row.webhook_url,
            delivery.attempts,
        )


def retry_due_open_api_webhooks(session: Session) -> int:
    return process_due_webhook_retries(session)
