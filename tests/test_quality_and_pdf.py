"""Quality and certificate PDF tests."""
from __future__ import annotations

import pytest

pytest.importorskip("fpdf")

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from voice_platform.job.schemas import AuthorizationCertificateResponse
from voice_platform.licensing.certificate_pdf import build_authorization_pdf

OWNER = UUID("00000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("11111111-1111-1111-1111-111111111101")
AUTH_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_build_authorization_pdf_bytes():
    cert = AuthorizationCertificateResponse(
        authorization_id=AUTH_ID,
        seller_user_id=OWNER,
        buyer_user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        voice_version_id=VERSION_ID,
        catalog_id=UUID("22222222-2222-2222-2222-222222222222"),
        voice_title="Test Voice",
        license_type="commercial_standard",
        char_quota_total=50000,
        char_quota_used=0,
        status="active",
        issued_at=datetime.now(timezone.utc),
        signature="abc123",
    )
    data = build_authorization_pdf(cert)
    assert data[:4] == b"%PDF"


def test_quality_evaluate_api(client):
    with patch("apps.api.routes.quality.QualityService") as svc_cls:
        svc_cls.return_value.evaluate.return_value = {
            "voice_version_id": str(VERSION_ID),
            "similarity_score": 0.92,
            "quality_pass": True,
            "threshold": 0.9,
            "eval_sentence": "hello",
            "ref_audio_url": "http://x/a.wav",
            "synth_audio_url": "http://x/b.wav",
            "method": "mock_embedding",
            "ab_vote_count": 0,
            "ref_pick_rate": None,
            "created_at": None,
            "updated_at": None,
        }
        r = client.post(
            f"/api/v1/voice-versions/{VERSION_ID}/quality/evaluate",
            headers={"X-User-Id": str(OWNER)},
        )
    assert r.status_code == 200
    assert r.json()["quality_pass"] is True


def test_certificate_pdf_api(client):
    with patch("apps.api.routes.licensing.LicensingService") as svc_cls:
        svc_cls.return_value.build_certificate_pdf.return_value = b"%PDF-mock-data"
        r = client.get(
            f"/api/v1/authorizations/{AUTH_ID}/certificate.pdf",
            headers={"X-User-Id": str(OWNER)},
        )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
