"""Intelligence API routes — LLM-powered smart features."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from apps.api.exceptions import raise_domain_http
from domains.intelligence.schemas import (
    ScriptPolishRequest,
    ScriptPolishResponse,
    SmartModerateRequest,
    SmartModerateResponse,
    SmartSynthParamsRequest,
    SmartSynthParamsResponse,
    SmartVoiceMatchRequest,
    SmartVoiceMatchResponse,
)
from domains.intelligence.service import IntelligenceService, IntelligenceServiceError
from fastapi import APIRouter, Depends, Query

router = APIRouter()
_service = IntelligenceService()


@router.post("/intelligence/synth-params", response_model=SmartSynthParamsResponse)
def recommend_synth_params(
    body: SmartSynthParamsRequest,
    _: UUID = Depends(get_current_user_id),
) -> SmartSynthParamsResponse:
    """AI 智能推荐合成参数（情感、语速、温度、音高）。"""
    try:
        return _service.recommend_synth_params(
            text=body.text,
            character_hint=body.character_hint,
            context_hint=body.context_hint,
        )
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)


@router.post("/intelligence/match-voice", response_model=SmartVoiceMatchResponse)
def match_voice(
    body: SmartVoiceMatchRequest,
    _: UUID = Depends(get_current_user_id),
) -> SmartVoiceMatchResponse:
    """AI 智能音色匹配 — 根据角色描述推荐最合适的音色。"""
    try:
        return _service.match_voice(body)
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)


@router.post("/intelligence/emotion", response_model=dict)
def analyze_emotion_smart(
    text: str = Query(min_length=1, max_length=5000, description="待分析文本"),
    use_llm: bool = Query(default=True, description="是否使用 LLM 增强分析"),
    _: UUID = Depends(get_current_user_id),
) -> dict:
    """AI 增强情感分析 — LLM 语义理解 + 关键词兜底。"""
    try:
        return _service.analyze_emotion_smart(text, use_llm=use_llm)
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)


@router.post("/intelligence/moderate", response_model=SmartModerateResponse)
def moderate_content(
    body: SmartModerateRequest,
    _: UUID = Depends(get_current_user_id),
) -> SmartModerateResponse:
    """AI 内容审核 — 智能检测违规内容。"""
    try:
        return _service.moderate_content(body)
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)


@router.post("/intelligence/voice-description", response_model=dict)
def generate_voice_description(
    voice_name: str = Query(min_length=1, max_length=64, description="音色名称"),
    tags: str | None = Query(default=None, description="现有标签，逗号分隔"),
    sample_text: str | None = Query(default=None, max_length=500, description="样音文本"),
    _: UUID = Depends(get_current_user_id),
) -> dict:
    """AI 智能生成音色馆文案（标题、描述、标签、适用场景）。"""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        return _service.generate_voice_description(
            voice_name=voice_name,
            tags=tag_list,
            sample_text=sample_text,
        )
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)


@router.post("/intelligence/polish-script", response_model=ScriptPolishResponse)
def polish_script(
    body: ScriptPolishRequest,
    _: UUID = Depends(get_current_user_id),
) -> ScriptPolishResponse:
    """AI 剧本智能润色 — 修正语法、统一角色名、增强旁白。"""
    try:
        return _service.polish_script(body)
    except IntelligenceServiceError as exc:
        raise_domain_http(exc)
