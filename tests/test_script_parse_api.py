from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_parse_smart_status_disabled(client):
    with patch("apps.api.routes.script._service") as svc:
        svc.status.return_value = {
            "enabled": False,
            "provider": "deepseek",
            "model": "deepseek-chat",
        }
        r = client.get("/api/v1/script/parse-smart/status")
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_parse_smart_disabled_returns_503(client):
    from domains.script.service import ScriptParseServiceError

    with patch("apps.api.routes.script._service") as svc:
        svc.parse_smart.side_effect = ScriptParseServiceError(
            "LLM_DISABLED",
            "AI 剧本分段未启用",
            503,
        )
        r = client.post(
            "/api/v1/script/parse-smart",
            json={"text": "方源说道，你给我出来。"},
        )
    assert r.status_code == 503
    assert r.json()["code"] == "LLM_DISABLED"


def test_parse_smart_mock_success(client):
    with patch("apps.api.routes.script._service") as svc:
        from voice_platform.script.schemas import ScreenplayLineSchema

        svc.parse_smart.return_value = [
            ScreenplayLineSchema(character="方源", text="你给我出来。"),
            ScreenplayLineSchema(character="白凝冰", text="你以为逃得掉吗？"),
        ]
        r = client.post(
            "/api/v1/script/parse-smart",
            json={"text": "方源冷笑道：你给我出来。白凝冰沉声道：你以为逃得掉吗？"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "llm"
    assert body["line_count"] == 2
    assert body["character_count"] == 2
    assert body["lines"][0]["character"] == "方源"


def test_parse_smart_service_mock_mode():
    from domains.script.service import ScriptParseService
    from voice_platform.config import Settings

    settings = Settings(
        script_parse_llm_enabled=True,
        deepseek_api_key="test-key",
    )
    settings.script.script_parse_llm_mock = True
    svc = ScriptParseService(settings=settings)
    lines = svc.parse_smart("方源说：白凝冰你给我出来")
    assert len(lines) == 2
    assert lines[0].character == "方源"


def test_parse_smart_parses_json_payload():
    from domains.script.service import ScriptParseService
    from voice_platform.config import Settings

    settings = Settings(
        script_parse_llm_enabled=True,
        deepseek_api_key="test-key",
    )
    svc = ScriptParseService(settings=settings)
    content = """```json
{"lines":[{"character":"旁白","text":"夜色渐深。"},{"character":"方源","text":"走。"}]}
```"""
    lines = svc._parse_llm_payload(content)
    assert len(lines) == 2
    assert lines[1].character == "方源"
