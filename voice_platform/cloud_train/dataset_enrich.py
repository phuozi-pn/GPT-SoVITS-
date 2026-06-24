"""DeepSeek / rule-based enrichment for cloud train dataset segments."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

from domains.intelligence.service import (
    EMOTION_LABELS,
    IntelligenceService,
    _call_llm,
    _llm_enabled,
    _parse_json_safe,
)
from voice_platform.config import Settings, get_settings
from voice_platform.emotion.analyzer import analyze_emotion, emotion_label

logger = logging.getLogger(__name__)

_ENRICH_SYSTEM = """你是中文语音训练数据专家。根据每段 ASR 转写，完成两件事：

1. **文本校正**：修正同音字、标点、口语断句；不得改变原意，不得增删整句或捏造内容。
2. **情感标注**：判断该段台词的主导情感。

只输出 JSON，格式严格为：
{
  "segments": [
    {
      "index": 0,
      "text": "校正后文本",
      "emotion": "neutral|happy|angry|sad|fearful|calm",
      "emotion_strength": 0.0-1.0,
      "notes": "可选，20字内说明"
    }
  ]
}

规则：
- 必须覆盖输入中的每个 index
- 混合情感选主导情感；旁白/叙述多为 neutral 或 calm
- 若 ASR 已很准确，text 可与原文相同
- 不要输出 markdown"""


@dataclass(frozen=True)
class SegmentEnrichment:
    index: int
    text_original: str
    text: str
    emotion: str
    emotion_label: str
    emotion_strength: float
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _keyword_enrich(index: int, text: str) -> SegmentEnrichment:
    emo, strength = analyze_emotion(text)
    if emo not in EMOTION_LABELS:
        emo = "neutral"
    return SegmentEnrichment(
        index=index,
        text_original=text,
        text=text,
        emotion=emo,
        emotion_label=emotion_label(emo),
        emotion_strength=round(strength, 3),
        notes="关键词情感标注",
    )


def _parse_llm_segments(content: str, originals: list[str]) -> list[SegmentEnrichment]:
    data = _parse_json_safe(content)
    rows = data.get("segments")
    if not isinstance(rows, list):
        raise ValueError("missing segments array")

    by_index: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        idx = int(row.get("index", -1))
        if idx < 0:
            continue
        by_index[idx] = row

    out: list[SegmentEnrichment] = []
    for i, original in enumerate(originals):
        row = by_index.get(i, {})
        text = str(row.get("text", original)).strip() or original
        emo = str(row.get("emotion", "neutral")).lower()
        if emo not in EMOTION_LABELS:
            emo = "neutral"
        strength = max(0.0, min(1.0, float(row.get("emotion_strength", 0.5))))
        notes = str(row.get("notes", ""))[:80]
        out.append(
            SegmentEnrichment(
                index=i,
                text_original=original,
                text=text,
                emotion=emo,
                emotion_label=EMOTION_LABELS.get(emo, "中性"),
                emotion_strength=round(strength, 3),
                notes=notes,
            )
        )
    return out


def enrich_dataset_segments(
    pairs: list[tuple[str, str]],
    *,
    settings: Settings | None = None,
    use_llm_enrich: bool | None = None,
) -> tuple[list[tuple[str, str]], list[SegmentEnrichment], str]:
    """Return updated pairs, per-segment metadata, and enrich mode (llm/keyword/off)."""
    if not pairs:
        return pairs, [], "off"

    settings = settings or get_settings()
    enabled = settings.train_dataset_llm_enrich if use_llm_enrich is None else bool(use_llm_enrich)
    if not enabled:
        return pairs, [], "off"

    texts = [text for _, text in pairs]

    if _llm_enabled(settings):
        payload = json.dumps(
            {"segments": [{"index": i, "text": t} for i, t in enumerate(texts)]},
            ensure_ascii=False,
        )
        try:
            raw = _call_llm(
                _ENRICH_SYSTEM,
                payload,
                temperature=0.2,
                response_format={"type": "json_object"},
                settings=settings,
            )
            meta = _parse_llm_segments(raw, texts)
            updated = [(path, meta[i].text) for i, (path, _) in enumerate(pairs)]
            return updated, meta, "llm"
        except Exception:
            logger.exception("dataset LLM enrich failed; falling back to keyword")

    meta = [_keyword_enrich(i, text) for i, text in enumerate(texts)]
    return pairs, meta, "keyword"
