"""根据音色馆标签生成通义万相封面 prompt。"""

from __future__ import annotations

GENDER_TAGS = {"男声", "女声", "童声", "中性声"}
ROLE_TAGS = {
    "男主", "女主", "男配", "女配", "反派", "路人", "龙套", "和尚", "道士", "老人",
    "少年", "少女", "旁白", "解说", "霸总", "母亲", "父亲", "丫鬟", "太监", "萌娃",
}
TRAIT_TAGS = {
    "温柔", "豪放", "细腻", "甜美", "御姐", "成熟", "低沉", "清亮", "磁性", "沙哑",
    "慵懒", "知性", "元气", "霸气", "洒脱", "沉稳", "俏皮", "冷艳", "温润", "凌厉",
    "深情", "克制", "厚重", "空灵", "邪魅", "坚毅", "软糯", "少年感",
}

GENDER_ZH = {"男声": "男性", "女声": "女性", "童声": "儿童", "中性声": "中性"}


def _partition(tags: list[str]) -> tuple[str | None, list[str], list[str]]:
    gender: str | None = None
    roles: list[str] = []
    traits: list[str] = []
    for tag in tags:
        if tag in GENDER_TAGS and gender is None:
            gender = tag
        elif tag in ROLE_TAGS:
            roles.append(tag)
        elif tag in TRAIT_TAGS:
            traits.append(tag)
    return gender, roles[:4], traits[:3]


def build_creator_avatar_prompt(*, display_name: str, bio: str = "") -> str:
    name = display_name.strip() or "配音创作者"
    bio_hint = bio.strip()[:80] if bio.strip() else "热爱声音创作"
    return (
        f"简约高级插画风格创作者头像，正方形构图，昵称「{name}」，"
        f"气质{bio_hint}，专业配音师形象，暖金米色背景，柔和光影，"
        f"无文字无水印，扁平插画，高品质"
    )


def build_catalog_cover_prompt(*, title: str, tags: list[str]) -> str:
    gender, roles, traits = _partition(tags)
    gender_phrase = GENDER_ZH.get(gender or "", "配音角色")
    role_phrase = "、".join(roles) if roles else "通用配音"
    trait_phrase = "、".join(traits) if traits else "沉稳、自然"
    title_bit = f"作品名《{title.strip()}》，" if title.strip() else ""
    return (
        f"{title_bit}简约高级插画风格配音角色头像，正方形构图，{gender_phrase}，"
        f"适合饰演{role_phrase}，声线气质{trait_phrase}，"
        f"暖金米色背景，柔和光影，无文字无水印，扁平插画，高品质"
    )
