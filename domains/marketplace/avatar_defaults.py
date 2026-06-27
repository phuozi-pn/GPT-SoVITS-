"""音色封面与创作者头像的默认插画 URL（与前端 catalogDisplay 逻辑一致）。"""

from __future__ import annotations

from uuid import UUID

GENDER_TAGS = frozenset({"男声", "女声", "童声", "中性声"})
ROLE_IMPLIES_GENDER: dict[str, str] = {
    "男主": "男声",
    "男配": "男声",
    "霸总": "男声",
    "父亲": "男声",
    "太监": "男声",
    "女主": "女声",
    "女配": "女声",
    "母亲": "女声",
    "丫鬟": "女声",
    "萌娃": "童声",
}

DEFAULT_COVER_MALE = "/catalog/covers/voice-male-01.svg"
DEFAULT_COVER_FEMALE = "/catalog/covers/voice-female-01.svg"


def resolve_gender_from_tags(tags: list[str]) -> str | None:
    gender: str | None = None
    for tag in tags:
        if tag in GENDER_TAGS:
            gender = tag
            break
    if gender:
        return gender
    for tag in tags:
        implied = ROLE_IMPLIES_GENDER.get(tag)
        if implied:
            return implied
    return None


def default_catalog_cover_url(tags: list[str]) -> str:
    gender = resolve_gender_from_tags(tags)
    if gender in {"女声", "童声"}:
        return DEFAULT_COVER_FEMALE
    return DEFAULT_COVER_MALE


def default_creator_avatar_url(*, user_id: UUID) -> str:
    """按用户 ID 稳定分配默认头像，避免全员相同。"""
    return DEFAULT_COVER_FEMALE if user_id.int % 2 else DEFAULT_COVER_MALE


def resolve_catalog_cover_url(*, tags: list[str], cover_image_url: str | None) -> str:
    if (cover_image_url or "").strip():
        return cover_image_url.strip()
    return default_catalog_cover_url(tags)


def resolve_creator_avatar_url(*, user_id: UUID, avatar_url: str | None) -> str:
    if (avatar_url or "").strip():
        return avatar_url.strip()
    return default_creator_avatar_url(user_id=user_id)
