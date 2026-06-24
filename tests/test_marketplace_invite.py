"""Tests for MVP+1 REQ-015 invite gate and quality_pass publish gate."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

OWNER = UUID("00000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("11111111-1111-1111-1111-111111111101")


@pytest.fixture
def client():
    from apps.api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_publish_eligibility_api(client):
    with patch("apps.api.routes.marketplace.MarketplaceInviteService") as svc_cls:
        svc_cls.return_value.get_publish_eligibility.return_value = {
            "can_publish": False,
            "invite_required": True,
            "invited": False,
            "on_waitlist": False,
            "quality_gate": True,
            "reason": "INVITE_REQUIRED",
            "message": "需要邀请码",
        }
        r = client.get("/api/v1/marketplace/publish-eligibility")
    assert r.status_code == 200
    assert r.json()["can_publish"] is False


def test_redeem_invite_api(client):
    with patch("apps.api.routes.marketplace.MarketplaceInviteService") as svc_cls:
        svc_cls.return_value.redeem_invite.return_value = {
            "invited": True,
            "code": "PHONIA-CREATOR",
            "message": "ok",
        }
        r = client.post(
            "/api/v1/marketplace/invite/redeem",
            json={"code": "PHONIA-CREATOR"},
        )
    assert r.status_code == 200
    assert r.json()["invited"] is True


def test_publish_blocked_without_invite(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        from domains.marketplace.service import MarketplaceServiceError

        svc_cls.return_value.publish_to_catalog.side_effect = MarketplaceServiceError(
            "INVITE_REQUIRED",
            "invite required",
            403,
        )
        r = client.post(
            "/api/v1/catalog/voices",
            json={
                "voice_version_id": str(VERSION_ID),
                "title": "test voice",
            },
        )
    assert r.status_code == 403
    body = r.json()
    detail = body.get("detail", body)
    assert detail["code"] == "INVITE_REQUIRED"


def test_publish_blocked_without_quality(client):
    with patch("apps.api.routes.catalog.MarketplaceService") as svc_cls:
        from domains.marketplace.service import MarketplaceServiceError

        svc_cls.return_value.publish_to_catalog.side_effect = MarketplaceServiceError(
            "QUALITY_REQUIRED",
            "quality required",
            403,
        )
        r = client.post(
            "/api/v1/catalog/voices",
            json={
                "voice_version_id": str(VERSION_ID),
                "title": "test voice",
            },
        )
    assert r.status_code == 403
    body = r.json()
    detail = body.get("detail", body)
    assert detail["code"] == "QUALITY_REQUIRED"


def test_csv_parse_optional_emotion_columns():
    from domains.projects.service import _parse_csv

    csv_text = (
        "role,text,emotion,emotion_strength,speed,pause\n"
        "hero,你好,angry,0.8,1.1,0.2\n"
    ).encode("utf-8")
    role_map = {"hero": uuid4()}
    lines = _parse_csv(csv_text, role_map)
    assert len(lines) == 1
    assert lines[0].emotion == "angry"
    assert lines[0].emotion_strength == 0.8
    assert lines[0].speed_factor == 1.1
    assert lines[0].pause_duration == 0.2


def test_invite_service_ensure_can_publish():
    session = MagicMock()
    with patch("domains.marketplace.invite_service.get_settings") as settings_cls:
        settings_cls.return_value.marketplace_invite_required = True
        with patch("domains.marketplace.invite_service.MarketplaceInviteRepository") as repo_cls:
            repo_cls.return_value.has_active_invite.return_value = False
            from domains.marketplace.invite_service import (
                MarketplaceInviteService,
                MarketplaceInviteServiceError,
            )

            svc = MarketplaceInviteService(session)
            with pytest.raises(MarketplaceInviteServiceError) as exc:
                svc.ensure_can_publish(user_id=OWNER)
            assert exc.value.code == "INVITE_REQUIRED"
