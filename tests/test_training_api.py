from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

VOICE = "11111111-1111-1111-1111-111111111100"
OTHER_VOICE = "99999999-9999-9999-9999-999999999999"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_train_rejects_forbidden(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls, patch(
        "apps.api.routes.voices.TrainingService"
    ) as svc_cls:
        kyc_cls.return_value.ensure_verified_for_train.return_value = None
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (None, False, False, False, False)
        r = client.post(
            f"/api/v1/voices/{OTHER_VOICE}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


def test_train_rejects_consent_required(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls, patch(
        "apps.api.routes.voices.TrainingService"
    ) as svc_cls:
        kyc_cls.return_value.ensure_verified_for_train.return_value = None
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (None, True, False, True, True)
        r = client.post(
            f"/api/v1/voices/{VOICE}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "CONSENT_REQUIRED"


def test_train_rejects_asset_not_ready(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls, patch(
        "apps.api.routes.voices.TrainingService"
    ) as svc_cls:
        kyc_cls.return_value.ensure_verified_for_train.return_value = None
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (None, True, True, False, False)
        r = client.post(
            f"/api/v1/voices/{VOICE}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
    assert r.status_code == 403
    assert r.json()["code"] == "ASSET_NOT_READY"


def test_train_rejects_invalid_model_tag(client):
    with patch("apps.api.routes.voices.KycService") as kyc_cls, patch(
        "apps.api.routes.voices.TrainingService"
    ) as svc_cls:
        kyc_cls.return_value.ensure_verified_for_train.return_value = None
        svc = svc_cls.return_value
        svc.resolve_train_inputs.return_value = (MagicMock(), True, True, True, True)
        r = client.post(
            f"/api/v1/voices/{VOICE}/train",
            json={"model_tag": "unknown-tag"},
        )
    assert r.status_code == 400
    assert r.json()["code"] == "INVALID_MODEL_TAG"
