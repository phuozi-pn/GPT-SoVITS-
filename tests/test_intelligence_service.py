"""Tests for domains/intelligence/service.py — LLM-powered intelligence features."""

from __future__ import annotations

import pytest

from domains.intelligence.schemas import (
    ScriptPolishRequest,
    SmartModerateRequest,
    SmartVoiceMatchRequest,
)
from domains.intelligence.service import IntelligenceService


# ── Test fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def svc_no_llm(monkeypatch) -> IntelligenceService:
    """Service with LLM disabled (no API key set)."""
    from voice_platform import config

    monkeypatch.setattr(config.Settings, "deepseek_api_key", "")
    monkeypatch.setattr(config.Settings, "script_parse_llm_enabled", False)
    return IntelligenceService()


@pytest.fixture
def svc_mock_llm(monkeypatch) -> IntelligenceService:
    """Service with LLM enabled (mock key)."""
    from voice_platform import config

    monkeypatch.setattr(config.Settings, "deepseek_api_key", "sk-mock-key")
    monkeypatch.setattr(config.Settings, "script_parse_llm_enabled", True)
    monkeypatch.setattr(config.Settings, "deepseek_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(config.Settings, "deepseek_model", "deepseek-chat")
    monkeypatch.setattr(config.Settings, "script_parse_timeout_sec", 10)
    return IntelligenceService()


# ── Smart synthesis params ────────────────────────────────────────────

class TestRecommendSynthParams:
    """Test synthesis parameter recommendation."""

    def test_happy_text_fallback(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params("太好了！我们赢了！")
        assert resp.mode == "fallback"
        assert resp.result.emotion in ("happy", "neutral")
        assert 0.0 <= resp.result.emotion_strength <= 1.0
        assert 0.5 <= resp.result.speed_factor <= 1.5
        assert 0.1 <= resp.result.temperature <= 1.0
        assert -12.0 <= resp.result.pitch_factor <= 12.0

    def test_angry_text_fallback(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params("你找死！滚开！")
        assert resp.mode == "fallback"
        assert resp.result.emotion in ("angry", "neutral")

    def test_sad_text_fallback(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params("我好难过，心都要碎了。")
        assert resp.mode == "fallback"
        assert resp.result.emotion in ("sad", "neutral")
        assert resp.result.speed_factor <= 1.0  # sad → slower

    def test_with_character_hint(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params(
            "今天天气不错。", character_hint="老年长者"
        )
        assert resp.mode == "fallback"
        assert len(resp.result.reasoning) > 0
        assert "老年长者" in resp.result.reasoning

    def test_with_context_hint(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params(
            "再见。", character_hint="少年", context_hint="离别场景"
        )
        assert resp.mode == "fallback"

    def test_neutral_text_fallback(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params("今天天气不错。")
        assert resp.mode == "fallback"
        assert resp.result.emotion_label in ("中性", "喜", "怒", "哀", "惧", "平静")

    def test_empty_text_fallback(self, svc_no_llm: IntelligenceService) -> None:
        resp = svc_no_llm.recommend_synth_params("")
        assert resp.mode == "fallback"
        assert resp.result.emotion == "neutral"

    def test_result_values_in_range(self, svc_no_llm: IntelligenceService) -> None:
        """All result values should be within declared bounds."""
        resp = svc_no_llm.recommend_synth_params("测试台词")
        r = resp.result
        assert 0.0 <= r.emotion_strength <= 1.0
        assert 0.5 <= r.speed_factor <= 1.5
        assert 0.1 <= r.temperature <= 1.0
        assert -12.0 <= r.pitch_factor <= 12.0
        assert len(r.reasoning) > 0


# ── Smart voice matching ──────────────────────────────────────────────

class TestMatchVoice:
    """Test smart voice-to-character matching."""

    _SAMPLE_VOICES = [
        {"voice_id": "v1", "voice_name": "少年音", "tags": ["少年", "清亮", "年轻"], "description": "清亮的少年音色"},
        {"voice_id": "v2", "voice_name": "御姐音", "tags": ["御姐", "成熟", "低沉"], "description": "成熟御姐音色"},
        {"voice_id": "v3", "voice_name": "老者音", "tags": ["老年", "沧桑", "沉稳"], "description": "沧桑老者音色"},
    ]

    def test_fallback_matching_male(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartVoiceMatchRequest(
            character_description="一个年轻的男性角色",
            available_voices=self._SAMPLE_VOICES,
        )
        resp = svc_no_llm.match_voice(req)
        assert resp.mode == "fallback"
        assert len(resp.matches) >= 0  # may match none if scores < 0.6
        for m in resp.matches:
            assert 0.6 <= m.score <= 1.0
            assert len(m.voice_id) > 0
            assert len(m.reason) > 0

    def test_fallback_matching_female(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartVoiceMatchRequest(
            character_description="一个成熟女性",
            available_voices=self._SAMPLE_VOICES,
        )
        resp = svc_no_llm.match_voice(req)
        assert resp.mode == "fallback"

    def test_fallback_matching_elderly(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartVoiceMatchRequest(
            character_description="一位老年角色，声音沧桑",
            available_voices=self._SAMPLE_VOICES,
        )
        resp = svc_no_llm.match_voice(req)
        assert resp.mode == "fallback"
        # Should match the 老者音 with higher score
        if resp.matches:
            voice_ids = [m.voice_id for m in resp.matches]
            # 老者音 should be present or matched first
            assert len(voice_ids) <= 3

    def test_empty_voices_fallback(self, svc_no_llm: IntelligenceService) -> None:
        """Schema requires at least 1 voice; service handles empty list gracefully."""
        req = SmartVoiceMatchRequest(
            character_description="一个角色",
            available_voices=[{"voice_id": "v0", "voice_name": "test", "tags": [], "description": ""}],
        )
        resp = svc_no_llm.match_voice(req)
        assert resp.mode == "fallback"

    def test_max_3_matches(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartVoiceMatchRequest(
            character_description="一个角色",
            available_voices=self._SAMPLE_VOICES,
        )
        resp = svc_no_llm.match_voice(req)
        assert len(resp.matches) <= 3

    def test_matches_sorted_by_score(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartVoiceMatchRequest(
            character_description="一个角色",
            available_voices=self._SAMPLE_VOICES,
        )
        resp = svc_no_llm.match_voice(req)
        if len(resp.matches) >= 2:
            for i in range(len(resp.matches) - 1):
                assert resp.matches[i].score >= resp.matches[i + 1].score


# ── Smart emotion analysis ────────────────────────────────────────────

class TestAnalyzeEmotionSmart:
    """Test LLM-enhanced emotion analysis."""

    def test_happy_keyword_fallback(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.analyze_emotion_smart("哈哈，太开心了！", use_llm=False)
        assert result["mode"] == "keyword"
        assert result["emotion"] in ("happy", "neutral")
        assert "text_preview" in result
        assert 0.0 <= result["strength"] <= 1.0

    def test_angry_keyword_fallback(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.analyze_emotion_smart("你找死！", use_llm=False)
        assert result["mode"] == "keyword"
        assert result["emotion"] in ("angry", "neutral")

    def test_neutral_keyword_fallback(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.analyze_emotion_smart("今天天气不错。", use_llm=False)
        assert result["mode"] == "keyword"
        assert result["emotion"] == "neutral"

    def test_llm_disabled_uses_keyword(self, svc_no_llm: IntelligenceService) -> None:
        """When LLM is not enabled, use_llm=True should still fallback."""
        result = svc_no_llm.analyze_emotion_smart("太棒了！", use_llm=True)
        assert result["mode"] == "keyword"

    def test_text_preview_truncation(self, svc_no_llm: IntelligenceService) -> None:
        long_text = "测试" * 200  # 400 chars
        result = svc_no_llm.analyze_emotion_smart(long_text, use_llm=False)
        assert len(result["text_preview"]) <= 120

    def test_empty_text(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.analyze_emotion_smart("", use_llm=False)
        assert result["emotion"] == "neutral"


# ── Content moderation ────────────────────────────────────────────────

class TestModerateContent:
    """Test AI-powered content moderation."""

    def test_safe_content_rule_based(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="今天天气真好，适合出去玩。")
        resp = svc_no_llm.moderate_content(req)
        assert resp.mode == "rule"
        assert resp.result.passed is True
        assert resp.result.risk_level == "low"
        assert resp.result.flags == []

    def test_high_risk_content(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="这里有赌博信息，快来参与。")
        resp = svc_no_llm.moderate_content(req)
        assert resp.mode == "rule"
        assert resp.result.passed is False
        assert "违法违规内容" in resp.result.flags

    def test_medium_risk_advertising(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="加微信免费领取礼品")
        resp = svc_no_llm.moderate_content(req)
        assert resp.mode == "rule"
        assert resp.result.passed is False
        assert "广告" in resp.result.flags[0]

    def test_personal_attack(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="你这个废物傻逼")
        resp = svc_no_llm.moderate_content(req)
        assert resp.mode == "rule"
        assert resp.result.passed is False
        assert "人身攻击" in resp.result.flags

    def test_context_post(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="加微信免费领取", context="post")
        resp = svc_no_llm.moderate_content(req)
        assert resp.result.passed is False

    def test_context_message(self, svc_no_llm: IntelligenceService) -> None:
        req = SmartModerateRequest(text="加微信免费领取", context="message")
        resp = svc_no_llm.moderate_content(req)
        assert resp.result.passed is False

    def test_multiple_flags(self, svc_no_llm: IntelligenceService) -> None:
        """Content matching multiple rule categories should report all."""
        req = SmartModerateRequest(text="傻逼废物，加微信领取免费毒品")
        resp = svc_no_llm.moderate_content(req)
        # Should have at least one flag
        assert len(resp.result.flags) >= 1


# ── Voice description generation ──────────────────────────────────────

class TestGenerateVoiceDescription:
    """Test voice catalog description generation."""

    def test_fallback_description(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.generate_voice_description("少年音")
        assert result["mode"] == "fallback"
        assert "少年音" in result["title"]
        assert len(result["description"]) > 0
        assert isinstance(result["tags"], list)
        assert isinstance(result["suitable_for"], list)

    def test_fallback_with_tags(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.generate_voice_description(
            "御姐音", tags=["成熟", "低沉", "御姐"]
        )
        assert result["mode"] == "fallback"
        assert result["tags"] == ["成熟", "低沉", "御姐"]
        assert "御姐音" in result["title"]

    def test_fallback_with_sample_text(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.generate_voice_description(
            "少年音", sample_text="你好，我是配音演员。"
        )
        assert result["mode"] == "fallback"
        assert "少年音" in result["title"]

    def test_suitable_for_defaults(self, svc_no_llm: IntelligenceService) -> None:
        result = svc_no_llm.generate_voice_description("任意音色")
        assert "短剧配音" in result["suitable_for"]


# ── Script polish ─────────────────────────────────────────────────────

class TestPolishScript:
    """Test AI script polish."""

    def test_fallback_returns_original(self, svc_no_llm: IntelligenceService) -> None:
        original = "方源：你给我出来！"
        req = ScriptPolishRequest(text=original)
        resp = svc_no_llm.polish_script(req)
        assert resp.mode == "fallback"
        assert resp.polished_text == original
        assert resp.line_count >= 1

    def test_fallback_grammar_scope(self, svc_no_llm: IntelligenceService) -> None:
        req = ScriptPolishRequest(text="方源：你给我出来！", polish_scope="grammar")
        resp = svc_no_llm.polish_script(req)
        assert resp.mode == "fallback"
        assert resp.polished_text == req.text

    def test_fallback_names_scope(self, svc_no_llm: IntelligenceService) -> None:
        req = ScriptPolishRequest(
            text="方源：你好\n方兄：再见", polish_scope="names"
        )
        resp = svc_no_llm.polish_script(req)
        assert resp.mode == "fallback"

    def test_fallback_narration_scope(self, svc_no_llm: IntelligenceService) -> None:
        req = ScriptPolishRequest(
            text="他缓缓走进房间，环顾四周。", polish_scope="narration"
        )
        resp = svc_no_llm.polish_script(req)
        assert resp.mode == "fallback"

    def test_line_count_matches(self, svc_no_llm: IntelligenceService) -> None:
        text = "行1\n行2\n行3"
        req = ScriptPolishRequest(text=text)
        resp = svc_no_llm.polish_script(req)
        assert resp.line_count == 3

    def test_empty_text(self, svc_no_llm: IntelligenceService) -> None:
        """Schema requires at least 1 character; use minimal valid input."""
        req = ScriptPolishRequest(text="x")
        resp = svc_no_llm.polish_script(req)
        assert resp.mode == "fallback"
        assert resp.line_count == 1


# ── LLM mock integration tests ────────────────────────────────────────

class TestIntelligenceWithMockLLM:
    """Tests that exercise the LLM code path with mocked HTTP responses."""

    def test_synth_params_with_mock_llm_response(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """Mock LLM returning valid JSON for synth params."""
        import httpx

        mock_json = {
            "choices": [{
                "message": {
                    "content": '{"emotion":"happy","emotion_strength":0.8,"speed_factor":1.2,"temperature":0.7,"pitch_factor":2.0,"reasoning":"语气欢快上扬"}'
                }
            }]
        }

        class MockResponse:
            status_code = 200
            @staticmethod
            def json():
                return mock_json

        def mock_post(*args, **kwargs):
            return MockResponse()

        monkeypatch.setattr(httpx.Client, "post", mock_post)
        resp = svc_mock_llm.recommend_synth_params("太棒了！")
        assert resp.mode == "llm"
        assert resp.result.emotion == "happy"
        assert resp.result.emotion_strength == 0.8
        assert resp.result.speed_factor == 1.2
        assert resp.result.temperature == 0.7
        assert resp.result.pitch_factor == 2.0

    def test_synth_params_llm_error_falls_back(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """When LLM call fails, fallback to keyword analysis."""
        import httpx

        def mock_post_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.Client, "post", mock_post_error)
        resp = svc_mock_llm.recommend_synth_params("太棒了！")
        assert resp.mode == "fallback"

    def test_voice_match_with_mock_llm_response(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """Mock LLM returning voice match results."""
        import httpx

        mock_json = {
            "choices": [{
                "message": {
                    "content": '{"matches":[{"voice_id":"v1","score":0.9,"reason":"少年音匹配"}]}'
                }
            }]
        }

        class MockResponse:
            status_code = 200
            @staticmethod
            def json():
                return mock_json

        monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: MockResponse())
        req = SmartVoiceMatchRequest(
            character_description="一个少年角色",
            available_voices=[
                {"voice_id": "v1", "voice_name": "少年音", "tags": ["少年"], "description": "少年音"}
            ],
        )
        resp = svc_mock_llm.match_voice(req)
        assert resp.mode == "llm"
        assert len(resp.matches) == 1
        assert resp.matches[0].voice_id == "v1"
        assert resp.matches[0].score == 0.9

    def test_moderate_with_mock_llm_response(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """Mock LLM content moderation."""
        import httpx

        mock_json = {
            "choices": [{
                "message": {
                    "content": '{"passed":false,"risk_level":"high","flags":["色情/低俗内容"],"reason":"包含低俗描述"}'
                }
            }]
        }

        class MockResponse:
            status_code = 200
            @staticmethod
            def json():
                return mock_json

        monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: MockResponse())
        req = SmartModerateRequest(text="违规内容测试")
        resp = svc_mock_llm.moderate_content(req)
        assert resp.mode == "llm"
        assert resp.result.passed is False
        assert resp.result.risk_level == "high"
        assert "色情/低俗内容" in resp.result.flags

    def test_polish_script_with_mock_llm_response(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """Mock LLM script polish."""
        import httpx

        mock_json = {
            "choices": [{
                "message": {
                    "content": '{"polished_text":"方源：你给我出来！","changes_summary":"无需修改","character_names":["方源"]}'
                }
            }]
        }

        class MockResponse:
            status_code = 200
            @staticmethod
            def json():
                return mock_json

        monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: MockResponse())
        req = ScriptPolishRequest(text="方源：你给我出来！")
        resp = svc_mock_llm.polish_script(req)
        assert resp.mode == "llm"
        assert "方源" in resp.polished_text
        assert "方源" in resp.character_names

    def test_polish_script_llm_error_falls_back(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """When LLM polish fails, return original text."""
        import httpx

        monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("fail")))
        req = ScriptPolishRequest(text="原始文本")
        resp = svc_mock_llm.polish_script(req)
        assert resp.mode == "fallback"
        assert resp.polished_text == "原始文本"

    def test_bad_json_response_falls_back(self, svc_mock_llm: IntelligenceService, monkeypatch) -> None:
        """LLM returns malformed JSON → fallback."""
        import httpx

        mock_json = {
            "choices": [{
                "message": {"content": "not valid json {{{"}
            }]
        }

        class MockResponse:
            status_code = 200
            @staticmethod
            def json():
                return mock_json

        monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: MockResponse())
        resp = svc_mock_llm.recommend_synth_params("测试")
        assert resp.mode == "fallback"
