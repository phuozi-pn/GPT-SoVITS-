"""KYC SaaS webhook handler tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from domains.kyc.service import KycService, KycServiceError

USER = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_saas_webhook_approves_user():
    session = MagicMock()
    user = MagicMock()
    user.verified = False
    body = json.dumps({"user_id": str(USER), "status": "approved", "note": "ok"}).encode()

    with (
        patch("domains.kyc.service.get_settings") as gs,
        patch.object(KycService, "__init__", lambda self, s: None),
    ):
        svc = KycService(session)
        svc._session = session
        svc._users = MagicMock()
        svc._audit = MagicMock()
        svc._settings = gs.return_value
        gs.return_value.kyc_saas_webhook_secret = "sec"
        gs.return_value.kyc_required = True
        gs.return_value.kyc_mock = False
        gs.return_value.kyc_provider = "saas"
        gs.return_value.kyc_saas_configured = True
        svc._users.get_by_id.return_value = user
        svc._users.set_verified = MagicMock()
        svc._audit.append = MagicMock()
        with patch.object(KycService, "get_status") as get_status:
            get_status.return_value = MagicMock(verified=True, provider="saas")
            result = svc.process_saas_webhook(body=body, signature=_sign(body, "sec"))
    assert result.verified is True
    svc._users.set_verified.assert_called_once()


def test_saas_webhook_invalid_signature():
    session = MagicMock()
    body = b'{"user_id":"x","status":"approved"}'

    with (
        patch("domains.kyc.service.get_settings") as gs,
        patch.object(KycService, "__init__", lambda self, s: None),
    ):
        svc = KycService(session)
        svc._settings = gs.return_value
        gs.return_value.kyc_saas_webhook_secret = "sec"
        with pytest.raises(KycServiceError) as exc:
            svc.process_saas_webhook(body=body, signature="bad")
    assert exc.value.code == "WEBHOOK_SIGNATURE_INVALID"
