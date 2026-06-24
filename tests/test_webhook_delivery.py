"""Webhook delivery retry tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from voice_platform.webhook.delivery import enqueue_webhook_delivery


@pytest.fixture
def session():
    return MagicMock()


def test_enqueue_webhook_retries_then_delivers(session):
    delivery_id = uuid4()
    row = MagicMock()
    row.id = delivery_id
    row.target_url = "https://example.com/hook"
    row.payload_json = {"event": "test"}
    row.signature_secret = "secret"
    row.max_attempts = 5
    row.attempts = 0
    row.status = "pending"

    delivered = MagicMock()
    delivered.status = "delivered"
    delivered.attempts = 1

    with (
        patch("voice_platform.webhook.delivery.WebhookDeliveryRepository") as repo_cls,
        patch("voice_platform.webhook.delivery._post_once") as post,
        patch("voice_platform.webhook.delivery.deliver_webhook") as deliver,
    ):
        repo_cls.return_value.create.return_value = row
        deliver.return_value = delivered
        result = enqueue_webhook_delivery(
            session,
            channel="open_api_job",
            target_url="https://example.com/hook",
            payload={"event": "test"},
            signature_secret="secret",
        )
    assert result.status == "delivered"


def test_post_once_signs_when_secret():
    from voice_platform.webhook.delivery import _post_once

    with patch("voice_platform.webhook.delivery.httpx.Client") as client_cls:
        resp = MagicMock()
        resp.status_code = 200
        client_cls.return_value.__enter__.return_value.post.return_value = resp
        ok, code, err = _post_once(
            target_url="https://example.com/hook",
            payload={"a": 1},
            signature_secret="s3cr3t",
        )
    assert ok is True
    assert code == 200
    headers = client_cls.return_value.__enter__.return_value.post.call_args.kwargs["headers"]
    assert "X-Webhook-Signature" in headers
