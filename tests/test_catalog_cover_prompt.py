"""Catalog cover prompt builder tests."""

from domains.marketplace.cover_prompt import build_catalog_cover_prompt


def test_build_catalog_cover_prompt_with_tags():
    prompt = build_catalog_cover_prompt(
        title="龙渊 · 沉稳男声",
        tags=["男声", "男主", "反派", "沉稳", "磁性"],
    )
    assert "龙渊" in prompt
    assert "男性" in prompt
    assert "男主" in prompt
    assert "沉稳" in prompt
    assert "无文字" in prompt


def test_normalize_dashscope_api_key_strips_prefix():
    from voice_platform.config import ImageGenConfig

    cfg = ImageGenConfig(dashscope_api_key="apiKey,sk-test-key")
    assert cfg.dashscope_api_key_normalized == "sk-test-key"


def test_build_catalog_cover_prompt_minimal():
    prompt = build_catalog_cover_prompt(title="", tags=[])
    assert "通用配音" in prompt
    assert "沉稳、自然" in prompt


def test_build_creator_avatar_prompt():
    from domains.marketplace.cover_prompt import build_creator_avatar_prompt

    prompt = build_creator_avatar_prompt(display_name="配音练习生", bio="短剧配音")
    assert "配音练习生" in prompt
    assert "短剧配音" in prompt
    assert "无文字" in prompt
