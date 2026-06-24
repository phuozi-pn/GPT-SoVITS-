"""Webhook delivery with inline retry and persisted audit."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from voice_platform.webhook.models import WebhookDeliveryRow
from voice_platform.webhook.repository import WebhookDeliveryRepository

logger = logging.getLogger(__name__)

_INLINE_RETRY_DELAYS_SEC = (0, 2, 5)


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _post_once(
    *,
    target_url: str,
    payload: dict,
    signature_secret: str | None,
    timeout_sec: float = 8.0,
) -> tuple[bool, int | None, str | None]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = (signature_secret or "").strip()
    if secret:
        headers["X-Webhook-Signature"] = sign_payload(secret, body)
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(target_url, content=body, headers=headers)
        if resp.status_code < 400:
            return True, resp.status_code, None
        return False, resp.status_code, resp.text[:300]
    except Exception as exc:
        return False, None, str(exc)[:300]


def deliver_webhook(
    session: Session,
    delivery_id: UUID,
    *,
    inline_retries: bool = True,
) -> WebhookDeliveryRow | None:
    repo = WebhookDeliveryRepository(session)
    row = repo.get(delivery_id)
    if not row or row.status in ("delivered", "failed"):
        return row

    attempts_left = row.max_attempts - row.attempts
    if attempts_left <= 0:
        return row

    inline_budget = min(len(_INLINE_RETRY_DELAYS_SEC), attempts_left) if inline_retries else 1
    for i in range(inline_budget):
        if i > 0:
            time.sleep(_INLINE_RETRY_DELAYS_SEC[i])
        success, status_code, err = _post_once(
            target_url=row.target_url,
            payload=row.payload_json,
            signature_secret=row.signature_secret,
        )
        row = repo.record_attempt(row, success=success, status_code=status_code, error=err)
        if success or row.status in ("delivered", "failed"):
            return row
    return row


def enqueue_webhook_delivery(
    session: Session,
    *,
    channel: str,
    target_url: str,
    payload: dict,
    signature_secret: str | None,
    max_attempts: int = 5,
) -> WebhookDeliveryRow:
    repo = WebhookDeliveryRepository(session)
    row = repo.create(
        channel=channel,
        target_url=target_url,
        payload=payload,
        signature_secret=signature_secret,
        max_attempts=max_attempts,
    )
    return deliver_webhook(session, row.id) or row


def process_due_webhook_retries(session: Session, *, limit: int = 10) -> int:
    repo = WebhookDeliveryRepository(session)
    due = repo.list_due_retries(limit=limit)
    for row in due:
        deliver_webhook(session, row.id, inline_retries=False)
    return len(due)
