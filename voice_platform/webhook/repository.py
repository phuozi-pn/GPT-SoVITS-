from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from voice_platform.webhook.models import WebhookDeliveryRow

_RETRY_DELAYS_SEC = (30, 120, 600, 3600)


class WebhookDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        channel: str,
        target_url: str,
        payload: dict,
        signature_secret: str | None,
        max_attempts: int = 5,
    ) -> WebhookDeliveryRow:
        row = WebhookDeliveryRow(
            id=uuid4(),
            channel=channel,
            target_url=target_url,
            payload_json=payload,
            signature_secret=signature_secret or None,
            max_attempts=max_attempts,
            status="pending",
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, delivery_id: UUID) -> WebhookDeliveryRow | None:
        return self._session.get(WebhookDeliveryRow, delivery_id)

    def record_attempt(
        self,
        row: WebhookDeliveryRow,
        *,
        success: bool,
        status_code: int | None,
        error: str | None,
    ) -> WebhookDeliveryRow:
        row.attempts += 1
        row.last_status_code = status_code
        row.last_error = (error or "")[:500] or None
        now = datetime.now(timezone.utc)
        if success:
            row.status = "delivered"
            row.delivered_at = now
            row.next_retry_at = None
        elif row.attempts >= row.max_attempts:
            row.status = "failed"
            row.next_retry_at = None
        else:
            row.status = "retrying"
            delay_idx = min(row.attempts - 1, len(_RETRY_DELAYS_SEC) - 1)
            row.next_retry_at = now + timedelta(seconds=_RETRY_DELAYS_SEC[delay_idx])
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_recent(self, *, limit: int = 50) -> list[WebhookDeliveryRow]:
        return list(
            self._session.scalars(
                select(WebhookDeliveryRow)
                .order_by(WebhookDeliveryRow.created_at.desc())
                .limit(limit)
            )
        )

    def list_due_retries(self, *, limit: int = 20) -> list[WebhookDeliveryRow]:
        now = datetime.now(timezone.utc)
        return list(
            self._session.scalars(
                select(WebhookDeliveryRow)
                .where(
                    WebhookDeliveryRow.status == "retrying",
                    WebhookDeliveryRow.next_retry_at.is_not(None),
                    WebhookDeliveryRow.next_retry_at <= now,
                )
                .order_by(WebhookDeliveryRow.next_retry_at.asc())
                .limit(limit)
            )
        )
