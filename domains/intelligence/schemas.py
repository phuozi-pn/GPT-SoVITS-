"""Schemas for AI intelligence domain."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Smart synthesis params ──────────────────────────────────────────

class SmartSynthParamsRequest(BaseModel):
    """Request body for smart synthesis parameter recommendation."""
    text: str = Field(min_length=1, max_length=5000, description="台词文本")
    character_hint: str | None = Field(default=None, max_length=64, description="角色提示（如'老年男性'、'活泼少女'）")
    context_hint: str | None = Field(default=None, max_length=500, description="上下文/场景提示")


class SmartSynthParamsResult(BaseModel):
    """LLM-recommended synthesis parameters."""
    emotion: str = Field(description="推荐情感: neutral/happy/angry/sad/fearful/calm")
    emotion_label: str = Field(description="情感中文标签")
    emotion_strength: float = Field(ge=0.0, le=1.0, description="情感强度 0-1")
    speed_factor: float = Field(ge=0.5, le=1.5, description="推荐语速 0.5-1.5")
    temperature: float = Field(ge=0.1, le=1.0, description="推荐温度 0.1-1.0")
    pitch_factor: float = Field(ge=-12.0, le=12.0, description="推荐音高偏移 -12~+12")
    reasoning: str = Field(max_length=300, description="AI 推荐理由简述")


class SmartSynthParamsResponse(BaseModel):
    """Response for smart synthesis parameter recommendation."""
    result: SmartSynthParamsResult
    mode: str = Field(default="llm", description="分析模式: llm / fallback")


# ── Smart voice matching ───────────────────────────────────────────

class SmartVoiceMatchRequest(BaseModel):
    """Request body for smart voice matching."""
    character_description: str = Field(
        min_length=1, max_length=1000,
        description="角色描述（如'20岁阳光少年，性格开朗'）",
    )
    available_voices: list[dict] = Field(
        min_length=1, max_length=50,
        description="候选音色列表，每项含 voice_id, voice_name, tags, description 等",
    )


class SmartVoiceMatchItem(BaseModel):
    voice_id: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200)


class SmartVoiceMatchResponse(BaseModel):
    matches: list[SmartVoiceMatchItem]
    mode: str = Field(default="llm")


# ── Smart content moderation ────────────────────────────────────────

class SmartModerateRequest(BaseModel):
    """Request body for AI content moderation."""
    text: str = Field(min_length=1, max_length=5000, description="待审核文本内容")
    context: str | None = Field(default=None, max_length=200, description="审核上下文: post / message / profile / voice_description")


class SmartModerateResult(BaseModel):
    passed: bool = Field(description="是否通过审核")
    risk_level: str = Field(description="风险等级: low / medium / high")
    flags: list[str] = Field(default_factory=list, description="标记的风险类别")
    reason: str = Field(max_length=300, description="审核理由")


class SmartModerateResponse(BaseModel):
    result: SmartModerateResult
    mode: str = Field(default="llm")


# ── Smart script polish ────────────────────────────────────────────

class ScriptPolishRequest(BaseModel):
    """Request body for AI script polish."""
    text: str = Field(min_length=1, max_length=8000, description="原始剧本/台词文本")
    polish_scope: str = Field(
        default="full",
        description="润色范围: full(全部) / grammar(仅语法) / names(仅统一角色名) / narration(仅旁白增强)",
    )


class ScriptPolishResponse(BaseModel):
    polished_text: str = Field(description="润色后的完整文本")
    changes_summary: str = Field(description="改动摘要")
    character_names: list[str] = Field(default_factory=list, description="识别到的角色名列表")
    line_count: int = Field(default=0, description="台词行数")
    mode: str = Field(default="llm")
