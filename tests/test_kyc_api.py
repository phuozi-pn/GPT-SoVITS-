"""REQ-002 KYC API tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

USER = "00000000-0000-0000-0000-000000000001"
ADMIN = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
VOICE = "11111111-1111-1111-1111-111111111100"
ADULT_ID = "110101199001011234"
MINOR_ID = "110101201501011234"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_kyc_status_unverified(client):
    with patch("apps.api.routes.kyc.KycService") as svc_cls:
        svc_cls.return_value.get_status.return_value = MagicMock(
            verified=False,
            verified_at=None,
            required=True,
            provider="mock",
        )
        r = client.get("/api/v1/kyc/status", headers={"X-User-Id": USER})
    assert r.status_code == 200
    assert r.json()["verified"] is False


def test_kyc_submit_adult_mock(client):
    with patch("apps.api.routes.kyc.KycService") as svc_cls:
        svc_cls.return_value.submit.return_value = MagicMock(
            verified=True,
            message="ok",
            audit_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )
        r = client.post(
            "/api/v1/kyc/submit",
            headers={"X-User-Id": USER},
            json={"real_name": "张三", "id_number": ADULT_ID},
        )
    assert r.status_code == 200
    assert r.json()["verified"] is True


def test_kyc_submit_minor_rejected(client):
    with patch("apps.api.routes.kyc.KycService") as svc_cls:
        from domains.kyc.service import KycServiceError

        svc_cls.return_value.submit.side_effect = KycServiceError(
            "KYC_MINOR_NOT_ALLOWED",
            "Minors cannot train voices",
            403,
        )
        r = client.post(
            "/api/v1/kyc/submit",
            headers={"X-User-Id": USER},
            json={"real_name": "小明", "id_number": MINOR_ID},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "KYC_MINOR_NOT_ALLOWED"


def test_train_requires_kyc(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls:
        from domains.kyc.service import KycServiceError

        kyc_cls.return_value.ensure_verified_for_train.side_effect = KycServiceError(
            "KYC_REQUIRED",
            "Real-name verification required before training",
            403,
        )
        r = client.post(
            f"/api/v1/voices/{VOICE}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "KYC_REQUIRED"


def test_admin_manual_verify(client):
    with patch("apps.api.routes.kyc.KycService") as svc_cls:
        svc_cls.return_value.admin_verify.return_value = MagicMock(
            verified=True,
            verified_at=None,
            required=True,
            provider="mock",
        )
        r = client.post(
            f"/api/v1/admin/kyc/{USER}/verify",
            headers={"X-User-Id": ADMIN},
            json={"note": "invite-only manual"},
        )
    assert r.status_code == 200
    assert r.json()["verified"] is True


def test_admin_kyc_pending(client):
    with patch("apps.api.routes.kyc.KycService") as svc_cls:
        from datetime import datetime, timezone

        svc_cls.return_value.list_pending_users.return_value = [
            MagicMock(
                user_id=USER,
                phone="13800000001",
                verified=False,
                verified_at=None,
                created_at=datetime.now(timezone.utc),
            )
        ]
        r = client.get("/api/v1/admin/kyc/pending", headers={"X-User-Id": ADMIN})
    assert r.status_code == 200
    assert len(r.json()) == 1
