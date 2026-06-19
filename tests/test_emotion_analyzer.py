"""REQ-027: Auto emotion detection unit tests."""

from __future__ import annotations

import pytest

from voice_platform.emotion.analyzer import (
    analyze_emotion,
    emotion_label,
)


class TestAnalyzeEmotion:
    """Test the keyword-based Chinese text emotion analyzer."""

    # ── Happy ──────────────────────────────────────────────
    @pytest.mark.parametrize(
        "text,expected_emotion",
        [
            ("哈哈，太棒了！我成功了！", "happy"),
            ("今天真开心，阳光明媚。", "happy"),
            ("太高兴了，终于等到这一天！", "happy"),
            ("嘻嘻，你好可爱啊。", "happy"),
            ("太好了！我们赢了！", "happy"),
            ("我非常喜欢这个声音。", "happy"),
            ("哈哈哈哈哈", "happy"),
            ("真的特别开心，谢谢大家。", "happy"),
        ],
    )
    def test_happy(self, text: str, expected_emotion: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == expected_emotion, f"Expected {expected_emotion}, got {emotion} for: {text}"
        assert 0.18 <= strength <= 1.0, f"Strength {strength} out of range for: {text}"

    # ── Angry ──────────────────────────────────────────────
    @pytest.mark.parametrize(
        "text,expected_emotion",
        [
            ("你找死！", "angry"),
            ("混蛋，凭什么这样对我！", "angry"),
            ("你以为你是谁？", "angry"),
            ("滚！我不想再见到你。", "angry"),
            ("非常愤怒，简直岂有此理。", "angry"),
        ],
    )
    def test_angry(self, text: str, expected_emotion: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == expected_emotion, f"Expected {expected_emotion}, got {emotion} for: {text}"
        assert strength >= 0.18

    # ── Sad ────────────────────────────────────────────────
    @pytest.mark.parametrize(
        "text,expected_emotion",
        [
            ("我好难过，心都要碎了。", "sad"),
            ("对不起，都是我的错。", "sad"),
            ("他走了，再也回不来了。", "sad"),
            ("泪水止不住地流。", "sad"),
            ("非常悲伤，感到无比绝望。", "sad"),
            ("我真的很后悔当初的决定。", "sad"),
        ],
    )
    def test_sad(self, text: str, expected_emotion: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == expected_emotion, f"Expected {expected_emotion}, got {emotion} for: {text}"
        assert strength >= 0.18

    # ── Fearful ────────────────────────────────────────────
    @pytest.mark.parametrize(
        "text,expected_emotion",
        [
            ("好可怕，我害怕极了。", "fearful"),
            ("谁在那里？救命啊！", "fearful"),
            ("不要过来！", "fearful"),
            ("我真的很担心会发生什么。", "fearful"),
            ("小心！有危险！", "fearful"),
        ],
    )
    def test_fearful(self, text: str, expected_emotion: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == expected_emotion, f"Expected {expected_emotion}, got {emotion} for: {text}"
        assert strength >= 0.18

    # ── Calm ───────────────────────────────────────────────
    @pytest.mark.parametrize(
        "text,expected_emotion",
        [
            ("没事，随它去吧。", "calm"),
            ("不必着急，慢慢来。", "calm"),
            ("平静地面对一切。", "calm"),
            ("算了，何必呢。", "calm"),
            ("他温和地说，没关系的。", "calm"),
        ],
    )
    def test_calm(self, text: str, expected_emotion: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == expected_emotion, f"Expected {expected_emotion}, got {emotion} for: {text}"
        assert strength >= 0.18

    # ── Neutral fallback ───────────────────────────────────
    @pytest.mark.parametrize(
        "text",
        [
            "今天天气不错。",
            "我们走吧。",
            "一个普通的句子。",
            "",
        ],
    )
    def test_neutral(self, text: str) -> None:
        emotion, strength = analyze_emotion(text)
        assert emotion == "neutral", f"Expected neutral, got {emotion} for: {text!r}"
        assert 0.0 < strength <= 1.0

    # ── Strength monotonicity ──────────────────────────────
    def test_intensity_boosters_increase_strength(self) -> None:
        """Intensity boosters like 非常 should increase strength."""
        _, mild = analyze_emotion("开心")
        _, strong = analyze_emotion("非常非常开心！")
        # With multiple boosters, strength should be >= mild
        assert strong >= mild * 0.8, f"Expected booster strength {strong} >= mild {mild}"

    def test_intensity_dampeners_decrease_strength(self) -> None:
        """Intensity dampeners like 有点 should decrease strength."""
        _, full = analyze_emotion("伤心")
        _, dampened = analyze_emotion("有点伤心…")
        assert dampened <= full + 0.1, f"Expected dampened {dampened} <= full {full} + 0.1"


class TestEmotionLabel:
    def test_known_labels(self) -> None:
        assert emotion_label("neutral") == "中性"
        assert emotion_label("happy") == "喜"
        assert emotion_label("angry") == "怒"
        assert emotion_label("sad") == "哀"
        assert emotion_label("fearful") == "惧"
        assert emotion_label("calm") == "平静"

    def test_unknown_label(self) -> None:
        assert emotion_label("unknown") == "未知"


class TestMixedEmotion:
    """Edge cases: text with conflicting emotion keywords."""

    def test_mixed_happy_sad_picks_stronger(self) -> None:
        """When both happy and sad keywords appear, pick the stronger signal."""
        emotion, strength = analyze_emotion("我很开心，但也很伤心。")
        assert emotion in ("happy", "sad"), f"Unexpected emotion {emotion}"
        assert strength >= 0.1

    def test_long_neutral_text(self) -> None:
        """Long text with no emotion keywords should be neutral."""
        long_text = (
            "从前有座山，山里有座庙，庙里有个老和尚和小和尚。"
            "老和尚给小和尚讲故事。"
        )
        emotion, _ = analyze_emotion(long_text)
        assert emotion == "neutral"


class TestEdgeCases:
    def test_single_char(self) -> None:
        emotion, strength = analyze_emotion("开心")
        assert emotion == "happy"
        assert strength >= 0.1

    def test_whitespace_only(self) -> None:
        emotion, strength = analyze_emotion("   ")
        assert emotion == "neutral"
        assert strength == 0.1

    def test_punctuation_only(self) -> None:
        emotion, strength = analyze_emotion("！？。")
        assert emotion == "neutral"
