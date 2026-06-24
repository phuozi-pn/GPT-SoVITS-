"""Open API developer webhook tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from voice_platform.developer.webhook import dispatch_open_api_job_webhook
from voice_platform.webhook.delivery import sign_payload


def test_sign_payload():
    body = b'{"event":"job.finished"}'
    sig = sign_payload("secret", body)
    assert len(sig) == 64


@patch("voice_platform.developer.webhook.enqueue_webhook_delivery")
def test_dispatch_open_api_job_webhook(mock_enqueue):
    session = MagicMock()
    key_id = uuid4()
    job_id = uuid4()
    row = MagicMock()
    row.webhook_url = "https://example.com/hook"
    row.webhook_secret = "whsec"
    delivery = MagicMock()
    delivery.status = "delivered"
    delivery.attempts = 1
    mock_enqueue.return_value = delivery

    with patch("voice_platform.developer.webhook.ApiKeyRepository") as repo_cls:
        repo_cls.return_value.get.return_value = row
        dispatch_open_api_job_webhook(
            session,
            api_key_id=key_id,
            job_id=job_id,
            status="succeeded",
            result={"audio_url": "http://x/a.wav"},
        )

    mock_enqueue.assert_called_once()
    call_kw = mock_enqueue.call_args.kwargs
    assert call_kw["target_url"] == "https://example.com/hook"
    assert call_kw["payload"]["job_id"] == str(job_id)
    assert call_kw["signature_secret"] == "whsec"


def test_update_webhook_api():
    from apps.api.main import create_app

    app = create_app()
    user = UUID("00000000-0000-0000-0000-000000000001")
    key_id = uuid4()
    with TestClient(app) as c:
        with patch("apps.api.routes.developer.DeveloperService") as svc_cls:
            svc_cls.return_value.update_webhook.return_value = {
                "key_id": str(key_id),
                "name": "test",
                "key_prefix": "vsk_abc",
                "scopes": ["synthesis:write", "jobs:read"],
                "revoked": False,
                "webhook_url": "https://example.com/hook",
                "last_used_at": None,
                "created_at": None,
            }
            r = c.patch(
                f"/api/v1/developer/api-keys/{key_id}/webhook",
                headers={"X-User-Id": str(user)},
                json={"webhook_url": "https://example.com/hook", "webhook_secret": "sec"},
            )
    assert r.status_code == 200
    assert r.json()["webhook_url"] == "https://example.com/hook"
