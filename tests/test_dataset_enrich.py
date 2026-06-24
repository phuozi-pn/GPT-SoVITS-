from __future__ import annotations

from unittest.mock import patch

from voice_platform.cloud_train.dataset_enrich import enrich_dataset_segments


def test_enrich_keyword_fallback():
    pairs = [("/seg/0.wav", "你给我滚！")]
    with patch("voice_platform.cloud_train.dataset_enrich._llm_enabled", return_value=False):
        updated, meta, mode = enrich_dataset_segments(
            pairs,
            settings=type("S", (), {"train_dataset_llm_enrich": True})(),
            use_llm_enrich=True,
        )
    assert mode == "keyword"
    assert meta[0].emotion in ("angry", "neutral")
    assert updated[0][1] == pairs[0][1]


def test_enrich_off_skips():
    pairs = [("/seg/0.wav", "你好")]
    updated, meta, mode = enrich_dataset_segments(
        pairs,
        settings=type("S", (), {"train_dataset_llm_enrich": False})(),
        use_llm_enrich=False,
    )
    assert mode == "off"
    assert meta == []
    assert updated == pairs


def test_enrich_llm_updates_text():
    pairs = [
        ("/seg/0.wav", "你好啊"),
        ("/seg/1.wav", "滚开"),
    ]
    llm_json = (
        '{"segments":[{"index":0,"text":"你好啊。","emotion":"happy","emotion_strength":0.6,"notes":"问候"},'
        '{"index":1,"text":"滚开！","emotion":"angry","emotion_strength":0.85,"notes":"呵斥"}]}'
    )
    with patch("voice_platform.cloud_train.dataset_enrich._llm_enabled", return_value=True):
        with patch("voice_platform.cloud_train.dataset_enrich._call_llm", return_value=llm_json):
            updated, meta, mode = enrich_dataset_segments(
                pairs,
                settings=type("S", (), {"train_dataset_llm_enrich": True})(),
                use_llm_enrich=True,
            )
    assert mode == "llm"
    assert updated[0][1] == "你好啊。"
    assert meta[1].emotion == "angry"
