"""LLM-powered intelligence service.

Provides:
- Smart synthesis parameter recommendation (emotion / speed / temperature / pitch)
- Smart voice-to-character matching
- AI content moderation
- Smart emotion analysis (LLM-enhanced, fallback to keyword)
- Smart voice description generation
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from domains.intelligence.schemas import (
    ScriptPolishRequest,
    ScriptPolishResponse,
    SmartModerateRequest,
    SmartModerateResult,
    SmartModerateResponse,
    SmartSynthParamsRequest,
    SmartSynthParamsResponse,
    SmartSynthParamsResult,
    SmartVoiceMatchItem,
    SmartVoiceMatchRequest,
    SmartVoiceMatchResponse,
)
from voice_platform.config import Settings, get_settings

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class IntelligenceServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _llm_enabled(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(s.deepseek_api_key.strip() and s.script_parse_llm_enabled)


def _call_llm(
    system_prompt: str,
    user_content: str,
    *,
    temperature: float = 0.3,
    response_format: dict | None = None,
    settings: Settings | None = None,
) -> str:
    """Call DeepSeek LLM with given prompts, return content string."""
    s = settings or get_settings()
    url = f"{s.deepseek_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": s.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {s.deepseek_api_key.strip()}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(s.script_parse_timeout_sec)

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise IntelligenceServiceError(
            "LLM_UNAVAILABLE", "无法连接 AI 服务", 502,
        ) from exc

    if resp.status_code >= 400:
        detail = resp.text[:240]
        raise IntelligenceServiceError(
            "LLM_ERROR", f"AI 服务返回错误 ({resp.status_code}): {detail}", 502,
        )

    try:
        body = resp.json()
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise IntelligenceServiceError(
            "LLM_BAD_RESPONSE", "AI 响应格式异常", 502,
        ) from exc


def _parse_json_safe(content: str) -> dict:
    """Safely parse LLM JSON output, stripping markdown fences."""
    raw = content.strip()
    fence = _JSON_FENCE.search(raw)
    if fence:
        raw = fence.group(1).strip()
    return json.loads(raw)


# ── Emotion labels ──────────────────────────────────────────────────

EMOTION_LABELS: dict[str, str] = {
    "neutral": "中性", "happy": "喜", "angry": "怒",
    "sad": "哀", "fearful": "惧", "calm": "平静",
}

_SYNTH_PARAMS_SYSTEM = """你是语音合成参数专家。根据台词内容和角色特征，推荐最佳合成参数。

只输出 JSON，格式严格为：
{
  "emotion": "happy|angry|sad|fearful|calm|neutral",
  "emotion_strength": 0.0-1.0,
  "speed_factor": 0.5-1.5,
  "temperature": 0.1-1.0,
  "pitch_factor": -12.0~12.0,
  "reasoning": "简短推荐理由（30字以内）"
}

规则：
1. 根据文本语义判断情感（不是关键词匹配，要理解上下文）
2. 愤怒/激动的台词：语速偏快(1.1-1.3)、temperature偏高(0.6-0.8)、pitch可能偏高
3. 悲伤/低落：语速偏慢(0.7-0.9)、temperature偏低(0.3-0.5)、pitch偏低
4. 平静叙述：语速适中(0.9-1.1)、temperature适中(0.5-0.7)
5. 高兴/欢快：语速偏快、temperature偏高
6. 恐惧/紧张：语速变化大、temperature偏高、pitch可能偏高
7. 如果有角色提示，结合角色年龄/性格调整
8. 不要输出 markdown 或其它说明文字"""


class IntelligenceService:
    """LLM-powered intelligence features."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ── Smart synthesis params ──────────────────────────────────

    def recommend_synth_params(
        self,
        text: str,
        character_hint: str | None = None,
        context_hint: str | None = None,
    ) -> SmartSynthParamsResponse:
        """Recommend synthesis parameters based on text semantics."""
        if not _llm_enabled(self._settings):
            return self._fallback_synth_params(text, character_hint)

        user_content = f"台词：{text}"
        if character_hint:
            user_content += f"\n角色：{character_hint}"
        if context_hint:
            user_content += f"\n场景：{context_hint}"

        try:
            raw = _call_llm(
                _SYNTH_PARAMS_SYSTEM,
                user_content,
                temperature=0.3,
                response_format={"type": "json_object"},
                settings=self._settings,
            )
            data = _parse_json_safe(raw)
            emotion = str(data.get("emotion", "neutral")).lower()
            if emotion not in EMOTION_LABELS:
                emotion = "neutral"

            result = SmartSynthParamsResult(
                emotion=emotion,
                emotion_label=EMOTION_LABELS.get(emotion, "中性"),
                emotion_strength=max(0.0, min(1.0, float(data.get("emotion_strength", 0.5)))),
                speed_factor=max(0.5, min(1.5, float(data.get("speed_factor", 1.0)))),
                temperature=max(0.1, min(1.0, float(data.get("temperature", 0.7)))),
                pitch_factor=max(-12.0, min(12.0, float(data.get("pitch_factor", 0.0)))),
                reasoning=str(data.get("reasoning", "AI 综合分析推荐"))[:300],
            )
            return SmartSynthParamsResponse(result=result, mode="llm")
        except Exception:
            return self._fallback_synth_params(text, character_hint)

    def _fallback_synth_params(
        self, text: str, character_hint: str | None = None
    ) -> SmartSynthParamsResponse:
        """Rule-based fallback when LLM is unavailable."""
        from voice_platform.emotion.analyzer import analyze_emotion, emotion_label

        emotion, strength = analyze_emotion(text)

        # Heuristic speed based on emotion
        speed_map = {
            "happy": 1.15, "angry": 1.2, "sad": 0.85,
            "fearful": 1.1, "calm": 0.95, "neutral": 1.0,
        }
        temp_map = {
            "happy": 0.7, "angry": 0.75, "sad": 0.5,
            "fearful": 0.7, "calm": 0.55, "neutral": 0.6,
        }
        pitch_map = {
            "happy": 2.0, "angry": 1.0, "sad": -1.5,
            "fearful": 3.0, "calm": 0.0, "neutral": 0.0,
        }

        result = SmartSynthParamsResult(
            emotion=emotion,
            emotion_label=emotion_label(emotion),
            emotion_strength=round(strength, 2),
            speed_factor=speed_map.get(emotion, 1.0),
            temperature=temp_map.get(emotion, 0.6),
            pitch_factor=pitch_map.get(emotion, 0.0),
            reasoning="基于关键词情感分析自动推荐" if not character_hint else f"基于角色'{character_hint}'和关键词分析推荐",
        )
        return SmartSynthParamsResponse(result=result, mode="fallback")

    # ── Smart voice matching ────────────────────────────────────

    def match_voice(
        self, request: SmartVoiceMatchRequest
    ) -> SmartVoiceMatchResponse:
        """Match best voices for a character description."""
        if not _llm_enabled(self._settings) or len(request.available_voices) == 0:
            return self._fallback_voice_match(request)

        voices_text = json.dumps(request.available_voices, ensure_ascii=False, indent=2)
        system = """你是配音选角专家。根据角色描述，从候选音色中选出最匹配的 TOP 3，并给出匹配理由。

只输出 JSON，格式严格为：
{"matches":[{"voice_id":"...","score":0.0-1.0,"reason":"..."}]}

规则：
1. 匹配角色年龄、性别、性格特征
2. 考虑音色标签(tags)和描述(description)
3. 按匹配度从高到低排序，最多返回 3 个
4. score>=0.6 才算有效匹配，低于 0.6 不返回
5. 不要输出 markdown 或其它说明文字"""

        user = f"角色描述：{request.character_description}\n候选音色：{voices_text}"

        try:
            raw = _call_llm(system, user, temperature=0.2, response_format={"type": "json_object"})
            data = _parse_json_safe(raw)
            matches_raw = data.get("matches", [])
            matches = []
            for m in matches_raw[:3]:
                score = float(m.get("score", 0))
                if score >= 0.6:
                    matches.append(SmartVoiceMatchItem(
                        voice_id=str(m.get("voice_id", "")),
                        score=min(score, 1.0),
                        reason=str(m.get("reason", ""))[:200],
                    ))
            return SmartVoiceMatchResponse(matches=matches, mode="llm")
        except Exception:
            return self._fallback_voice_match(request)

    def _fallback_voice_match(
        self, request: SmartVoiceMatchRequest
    ) -> SmartVoiceMatchResponse:
        """Simple tag-based fallback matching."""
        desc_lower = request.character_description.lower()
        matches: list[SmartVoiceMatchItem] = []

        for v in request.available_voices[:10]:
            score = 0.5  # base score
            name = str(v.get("voice_name", "")).lower()
            tags = [str(t).lower() for t in v.get("tags", []) if t]
            vdesc = str(v.get("description", "")).lower()

            # Simple keyword matching
            for keyword in ["男", "male", "man", "boy"]:
                if keyword in desc_lower and (keyword in name or keyword in tags or keyword in vdesc):
                    score += 0.2
            for keyword in ["女", "female", "woman", "girl"]:
                if keyword in desc_lower and (keyword in name or keyword in tags or keyword in vdesc):
                    score += 0.2
            for keyword in ["少年", "青年", "年轻"]:
                if keyword in desc_lower and keyword in tags:
                    score += 0.15
            for keyword in ["中年", "老年", "成熟"]:
                if keyword in desc_lower and keyword in tags:
                    score += 0.15
            if any(kw in desc_lower for kw in ["甜", "温柔", "可爱"]) and "甜美" in (name + " ".join(tags)):
                score += 0.2
            if any(kw in desc_lower for kw in ["霸气", "威严", "冷酷"]) and ("霸气" in tags or "低沉" in tags):
                score += 0.2

            score = min(score, 0.95)
            if score >= 0.6:
                matches.append(SmartVoiceMatchItem(
                    voice_id=str(v.get("voice_id", "")),
                    score=round(score, 2),
                    reason=f"标签匹配度 {score:.0%}",
                ))

        matches.sort(key=lambda x: x.score, reverse=True)
        return SmartVoiceMatchResponse(matches=matches[:3], mode="fallback")

    # ── Smart emotion analysis (LLM-enhanced) ───────────────────

    def analyze_emotion_smart(
        self, text: str, use_llm: bool = True
    ) -> dict[str, Any]:
        """LLM-enhanced emotion analysis with keyword fallback."""
        if use_llm and _llm_enabled(self._settings):
            return self._llm_emotion(text)
        return self._keyword_emotion(text)

    def _llm_emotion(self, text: str) -> dict[str, Any]:
        system = """你是中文情感分析专家。分析台词的情感色彩。

只输出 JSON，格式严格为：
{"emotion":"happy|angry|sad|fearful|calm|neutral","emotion_label":"中文标签","strength":0.0-1.0,"analysis":"简短分析(20字内)"}

规则：
1. 理解语义而非仅看关键词
2. 混合情感选主导情感
3. 反问/讽刺要准确识别
4. 不要输出 markdown"""
        try:
            raw = _call_llm(system, text, temperature=0.2, response_format={"type": "json_object"})
            data = _parse_json_safe(raw)
            emotion = str(data.get("emotion", "neutral")).lower()
            if emotion not in EMOTION_LABELS:
                emotion = "neutral"
            return {
                "emotion": emotion,
                "emotion_label": EMOTION_LABELS.get(emotion, "中性"),
                "strength": max(0.0, min(1.0, float(data.get("strength", 0.5)))),
                "text_preview": text[:120],
                "mode": "llm",
            }
        except Exception:
            return self._keyword_emotion(text)

    def _keyword_emotion(self, text: str) -> dict[str, Any]:
        from voice_platform.emotion.analyzer import analyze_emotion, emotion_label

        emotion, strength = analyze_emotion(text)
        return {
            "emotion": emotion,
            "emotion_label": emotion_label(emotion),
            "strength": round(strength, 3),
            "text_preview": text[:120],
            "mode": "keyword",
        }

    # ── AI content moderation ───────────────────────────────────

    def moderate_content(self, request: SmartModerateRequest) -> SmartModerateResponse:
        """AI-powered content moderation."""
        if not _llm_enabled(self._settings):
            return self._rule_based_moderate(request)

        system = """你是内容安全审核专家。审核用户生成内容，判断是否违规。

只输出 JSON，格式严格为：
{"passed":true|false,"risk_level":"low|medium|high","flags":["类别1","类别2"],"reason":"审核理由(50字内)"}

违规类别包括但不限于：
- 色情/低俗内容
- 暴力/血腥描述
- 仇恨言论/歧视
- 诈骗/钓鱼信息
- 政治敏感内容
- 人身攻击/辱骂
- 广告/垃圾信息
- 违法违规内容

规则：
1. 严格但不误判正常内容
2. risk_level: low=基本安全, medium=疑似违规需人工复核, high=明确违规
3. 正常内容 passed=true, flags 为空
4. 不要输出 markdown"""

        ctx_label = {"post": "社区帖子", "message": "私信", "profile": "个人简介", "voice_description": "音色描述"}.get(
            request.context or "", "用户内容"
        )
        user = f"审核场景：{ctx_label}\n待审核内容：{request.text}"

        try:
            raw = _call_llm(system, user, temperature=0.1, response_format={"type": "json_object"})
            data = _parse_json_safe(raw)
            result = SmartModerateResult(
                passed=bool(data.get("passed", True)),
                risk_level=str(data.get("risk_level", "low")),
                flags=[str(f) for f in data.get("flags", []) if f],
                reason=str(data.get("reason", ""))[:300],
            )
            return SmartModerateResponse(result=result, mode="llm")
        except Exception:
            return self._rule_based_moderate(request)

    def _rule_based_moderate(self, request: SmartModerateRequest) -> SmartModerateResponse:
        """Basic keyword-based moderation fallback."""
        text = request.text.lower()
        flags: list[str] = []

        high_risk = ["赌博", "博彩", "毒品", "枪支", "洗钱"]
        medium_risk = ["广告", "加微信", "加QQ", "点击链接", "免费领取"]
        low_risk = ["傻逼", "废物", "去死"]

        for kw in high_risk:
            if kw in text:
                flags.append("违法违规内容")
                break
        for kw in medium_risk:
            if kw in text:
                flags.append("广告/垃圾信息")
                break
        for kw in low_risk:
            if kw in text:
                flags.append("人身攻击")
                break

        if flags:
            result = SmartModerateResult(
                passed=False,
                risk_level="medium" if "广告" in flags[0] else "high",
                flags=flags,
                reason=f"检测到敏感关键词",
            )
        else:
            result = SmartModerateResult(
                passed=True, risk_level="low", flags=[], reason="未检测到违规内容",
            )
        return SmartModerateResponse(result=result, mode="rule")

    # ── Voice description generation ────────────────────────────

    def generate_voice_description(
        self, voice_name: str, tags: list[str] | None = None, sample_text: str | None = None
    ) -> dict[str, Any]:
        """Generate marketing description for a voice in the catalog."""
        if not _llm_enabled(self._settings):
            return self._fallback_voice_desc(voice_name, tags)

        system = """你是音色产品文案专家。为音色馆的音色生成吸引人的介绍文案。

只输出 JSON，格式严格为：
{"title":"一句话标题(15字内)","description":"详细介绍(100字内)","tags":["标签1","标签2","标签3"],"suitable_for":["适用场景1","适用场景2"]}

规则：
1. 突出音色特点和适用场景
2. 文案有吸引力但不夸张
3. tags 3-5个，与音色特征相关
4. 不要输出 markdown"""

        user = f"音色名称：{voice_name}"
        if tags:
            user += f"\n现有标签：{', '.join(tags)}"
        if sample_text:
            user += f"\n样音文本：{sample_text}"

        try:
            raw = _call_llm(system, user, temperature=0.6, response_format={"type": "json_object"})
            data = _parse_json_safe(raw)
            return {
                "title": str(data.get("title", voice_name))[:30],
                "description": str(data.get("description", ""))[:200],
                "tags": [str(t) for t in data.get("tags", [])[:5]],
                "suitable_for": [str(s) for s in data.get("suitable_for", [])[:5]],
                "mode": "llm",
            }
        except Exception:
            return self._fallback_voice_desc(voice_name, tags)

    def _fallback_voice_desc(
        self, voice_name: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        return {
            "title": voice_name,
            "description": f"「{voice_name}」是一款优质 AI 音色，适用于短剧配音、有声书等场景。",
            "tags": tags or [],
            "suitable_for": ["短剧配音", "有声内容"],
            "mode": "fallback",
        }

    # ── Script polish ──────────────────────────────────────────

    _POLISH_SYSTEM_FULL = """你是专业短剧剧本编辑。润色剧本，使其更适合 AI 配音合成。

只输出 JSON，格式严格为：
{"polished_text":"完整润色后的文本","changes_summary":"改动说明(50字内)","character_names":["角色1","角色2"]}

规则：
1. 修正语法错误和错别字
2. 统一角色名（全文中同一角色的不同称呼统一为一个）
3. 将动作/环境描写转为"旁白"角色
4. 保持原文风格和情节不变
5. 为纯叙述文本添加合适的"角色：台词"格式
6. 不要编造原文没有的对话内容
7. polished_text 是润色后的完整原始文本，保持原有的换行和格式
8. 不要输出 markdown"""

    _POLISH_SYSTEM_GRAMMAR = """你是中文校对专家。仅修正语法错误和错别字，不改变内容和格式。

只输出 JSON，格式严格为：
{"polished_text":"修正后的文本","changes_summary":"改动说明(30字内)","character_names":[]}

规则：
1. 仅修正错别字和明显语法错误
2. 不改变角色名、情节、格式
3. 不要输出 markdown"""

    _POLISH_SYSTEM_NAMES = """你是剧本角色名统一专家。将全文中同一角色的不同称呼统一。

只输出 JSON，格式严格为：
{"polished_text":"统一角色名后的文本","changes_summary":"统一了哪些角色名(30字内)","character_names":["统一后的角色名列表"]}

规则：
1. 识别同一角色的不同称呼（如"方源"和"方兄"、"源哥"统一为"方源"）
2. 保持原文情节和格式不变
3. 不要输出 markdown"""

    _POLISH_SYSTEM_NARRATION = """你是剧本旁白增强专家。为剧本中的动作/环境描写添加"旁白"角色标注。

只输出 JSON，格式严格为：
{"polished_text":"增强后的文本","changes_summary":"添加了旁白标注(30字内)","character_names":["识别到的角色名"]}

规则：
1. 将动作/环境/心理描写转为"旁白：xxx"格式
2. 已有角色标注的对话保持不变
3. 旁白内容简洁有力，适合 AI 配音
4. 不要输出 markdown"""

    def polish_script(self, request: ScriptPolishRequest) -> ScriptPolishResponse:
        """AI script polish — fix grammar, unify names, enhance narration."""
        if not _llm_enabled(self._settings):
            return ScriptPolishResponse(
                polished_text=request.text,
                changes_summary="AI 服务未启用，返回原文",
                character_names=[],
                line_count=request.text.count("\n") + 1,
                mode="fallback",
            )

        scope = request.polish_scope
        if scope == "grammar":
            system = self._POLISH_SYSTEM_GRAMMAR
        elif scope == "names":
            system = self._POLISH_SYSTEM_NAMES
        elif scope == "narration":
            system = self._POLISH_SYSTEM_NARRATION
        else:
            system = self._POLISH_SYSTEM_FULL

        try:
            raw = _call_llm(
                system, request.text,
                temperature=0.3, response_format={"type": "json_object"},
                settings=self._settings,
            )
            data = _parse_json_safe(raw)
            polished = str(data.get("polished_text", request.text))
            return ScriptPolishResponse(
                polished_text=polished,
                changes_summary=str(data.get("changes_summary", ""))[:100],
                character_names=[str(n) for n in data.get("character_names", [])[:20]],
                line_count=polished.count("\n") + 1,
                mode="llm",
            )
        except Exception:
            return ScriptPolishResponse(
                polished_text=request.text,
                changes_summary="AI 处理异常，返回原文",
                character_names=[],
                line_count=request.text.count("\n") + 1,
                mode="fallback",
            )
