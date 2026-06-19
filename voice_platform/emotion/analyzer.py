"""
REQ-027: Auto emotion detection from Chinese text using keyword-based lexicon analysis.

Approach:
- No external ML dependencies (pure Python, based on Chinese emotion lexicon)
- Weighted keyword matching with intensity modifiers
- Returns emotion label + confidence strength

Supported emotions (aligned with REQ-008):
  neutral, happy, angry, sad, fearful, calm
"""

from __future__ import annotations

import re

# ── Emotion keyword lexicons (Chinese) ──────────────────────────────
# Each emotion has: base_keywords, intensity_modifiers
# Intensity modifiers scale the base strength (e.g., "非常" boosts, "有点" dampens)

EMOTION_LEXICON: dict[str, dict[str, list[str]]] = {
    "happy": {
        "keywords": [
            # Strong positive
            "哈哈", "呵呵", "嘻嘻", "嘿嘿", "开心", "高兴", "快乐", "愉快",
            "欢喜", "喜悦", "欣喜", "兴奋", "激动", "太好了", "太棒了",
            "真棒", "真好", "太好了", "很好", "非常好",
            # Smile / laugh
            "微笑", "大笑", "欢笑", "莞尔",
            # Love / affection
            "喜欢", "可爱", "美好", "甜蜜", "温暖", "温馨",
            # Success / achievement
            "成功了", "赢了", "胜利",
        ],
    },
    "angry": {
        "keywords": [
            # Direct anger
            "生气", "愤怒", "恼怒", "气愤", "恼火", "可恶", "可恨",
            "该死", "混蛋", "滚", "找死", "放肆", "大胆",
            # Frustration
            "凭什么", "为什么", "怎么可以", "怎么这样", "岂有此理",
            # Confrontational
            "你以为", "你敢", "不信", "少废话", "住口", "闭嘴",
            # Aggressive
            "杀", "打", "揍", "灭", "毁", "砸",
        ],
    },
    "sad": {
        "keywords": [
            # Direct sadness
            "难过", "伤心", "悲伤", "悲痛", "哀伤", "忧伤", "悲凉",
            "凄凉", "心酸", "心碎", "心如刀绞", "肝肠寸断",
            # Crying
            "哭", "哭泣", "流泪", "泪流", "落泪", "泪", "呜咽", "哽咽",
            # Loneliness
            "孤独", "寂寞", "孤单",
            # Loss / regret
            "对不起", "抱歉", "遗憾", "后悔", "如果", "要是",
            "失去", "离去", "离开", "走了", "不在了",
            # Helplessness
            "无望", "绝望", "无助", "没救了",
            # Pain / suffering
            "痛苦", "苦", "痛", "疼",
        ],
    },
    "fearful": {
        "keywords": [
            # Direct fear
            "害怕", "恐惧", "惊恐", "恐慌", "畏惧", "可怕", "吓",
            "吓人", "吓死", "好怕",
            # Anxiety
            "紧张", "不安", "担心", "担忧", "忐忑", "慌乱",
            # Threat
            "危险", "小心", "不要", "别过来", "救命", "救命啊",
            "谁", "什么东西", "有鬼", "幽灵",
            # Trembling
            "颤抖", "发抖", "哆嗦", "冒汗", "冷汗",
        ],
    },
    "calm": {
        "keywords": [
            # Peaceful
            "平静", "宁静", "安静", "安详", "安然", "淡然", "从容",
            "淡定", "平和", "温和", "温柔", "柔和",
            # Meditative / thoughtful
            "慢慢", "缓缓", "轻轻", "悠悠", "徐徐",
            # Acceptance
            "没事", "没关系", "随它去", "算了", "罢了",
            "不必", "不用", "无须",
            # Certainty / steady
            "一定", "肯定", "自然", "当然", "果然",
        ],
    },
}

# Intensity modifiers: boost or dampen emotion strength
INTENSITY_BOOSTERS: list[str] = [
    "非常", "十分", "特别", "极其", "极度", "无比", "太", "好",
    "真的", "实在", "真是", "绝对", "彻底", "万分", "超级",
]

INTENSITY_DAMPENERS: list[str] = [
    "有点", "有些", "稍微", "略微", "一点点", "不太", "不怎么",
    "还算", "勉强", "几乎",
]

# Punctuation indicators
EXCLAMATION_PATTERN = re.compile(r"[!！]{1,}")
QUESTION_PATTERN = re.compile(r"[?？]{1,}")
ELLIPSIS_PATTERN = re.compile(r"\.{2,}|…{1,}")


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many unique keywords appear in the text."""
    hits = 0
    for kw in keywords:
        if kw in text:
            hits += 1
    return hits


def _intensity_modifier(text: str) -> float:
    """Compute intensity multiplier from boosters and dampeners."""
    boost = sum(1 for b in INTENSITY_BOOSTERS if b in text)
    dampen = sum(1 for d in INTENSITY_DAMPENERS if d in text)
    modifier = 1.0 + boost * 0.15 - dampen * 0.15

    # Punctuation cues
    if EXCLAMATION_PATTERN.search(text):
        modifier += 0.1
    if QUESTION_PATTERN.search(text):
        modifier -= 0.05
    if ELLIPSIS_PATTERN.search(text):
        modifier -= 0.05

    return max(0.1, min(1.0, modifier))


def analyze_emotion(text: str) -> tuple[str, float]:
    """
    Analyze Chinese text and return (emotion_label, strength).

    Returns one of: neutral, happy, angry, sad, fearful, calm
    Strength is 0.0-1.0 representing confidence.

    Falls back to 'neutral' with low strength if no strong signal.
    """
    if not text or not text.strip():
        return "neutral", 0.1

    cleaned = text.strip()

    # Score each emotion
    scores: dict[str, float] = {}
    for emotion, data in EMOTION_LEXICON.items():
        hits = _count_keyword_hits(cleaned, data["keywords"])
        if hits >= 1:
            # Sigmoid-like normalization: hits of 1→0.3, 2→0.5, 3→0.65, 5→0.8, 10+→0.95
            raw = min(hits / (hits + 2.5), 0.95)
            modifier = _intensity_modifier(cleaned)
            scores[emotion] = round(raw * modifier, 3)

    if not scores:
        # No emotion keywords detected → neutral
        return "neutral", 0.3

    # Pick the highest-scoring emotion
    best = max(scores, key=lambda k: scores[k])
    strength = min(scores[best], 1.0)

    # If strongest signal is still weak, return neutral
    if strength < 0.18:
        return "neutral", max(0.2, strength)

    return best, strength


EMOTION_LABELS: dict[str, str] = {
    "neutral": "中性",
    "happy": "喜",
    "angry": "怒",
    "sad": "哀",
    "fearful": "惧",
    "calm": "平静",
}


def emotion_label(emotion: str) -> str:
    """Return Chinese display label for an emotion key."""
    return EMOTION_LABELS.get(emotion, "未知")
