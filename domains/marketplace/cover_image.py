"""音色馆封面：通义万相生成并落盘。"""

from __future__ import annotations

from uuid import UUID, uuid4

from domains.marketplace.cover_prompt import build_catalog_cover_prompt, build_creator_avatar_prompt
from voice_platform.config import get_settings
from voice_platform.image.wanx import WanxClient, WanxError
from voice_platform.storage.local import LocalStorage


def to_public_files_url(rel_path: str) -> str:
    """返回前端可代理的相对 URL（/files/...）。"""
    return f"/files/{rel_path.lstrip('/')}"


class CatalogCoverError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def generate_and_store_catalog_cover(
    *,
    owner_user_id: UUID,
    title: str,
    tags: list[str],
    catalog_id: UUID | None = None,
    prompt: str | None = None,
) -> tuple[str, str]:
    """返回 (public_url, prompt)。"""
    settings = get_settings()
    if not settings.catalog_cover_gen_enabled:
        raise CatalogCoverError(
            "COVER_GEN_DISABLED",
            "封面 AI 生成未启用，请设置 CATALOG_COVER_GEN_ENABLED=true",
            503,
        )
    client = WanxClient()
    if not client.enabled:
        raise CatalogCoverError(
            "WANX_NOT_CONFIGURED",
            "未配置 DASHSCOPE_API_KEY",
            503,
        )

    final_prompt = (prompt or "").strip() or build_catalog_cover_prompt(title=title, tags=tags)
    try:
        png = client.generate_png(prompt=final_prompt)
    except WanxError as exc:
        raise CatalogCoverError(exc.code, exc.message, 502) from exc

    file_id = catalog_id or uuid4()
    storage = LocalStorage()
    rel = storage.save_bytes(
        user_id=owner_user_id,
        job_id=file_id,
        data=png,
        ext="png",
        relative_name=f"catalog/covers/{file_id}.png",
    )
    return to_public_files_url(rel), final_prompt


def upload_and_store_catalog_cover(
    *,
    owner_user_id: UUID,
    data: bytes,
    ext: str,
    catalog_id: UUID | None = None,
) -> str:
    if not data:
        raise CatalogCoverError("EMPTY_FILE", "上传文件为空", 400)
    if len(data) > 5 * 1024 * 1024:
        raise CatalogCoverError("FILE_TOO_LARGE", "封面图不能超过 5MB", 400)
    normalized_ext = ext.lower().lstrip(".")
    if normalized_ext not in {"png", "jpg", "jpeg", "webp"}:
        raise CatalogCoverError("INVALID_IMAGE", "仅支持 png / jpg / webp", 400)
    if normalized_ext == "jpeg":
        normalized_ext = "jpg"

    file_id = catalog_id or uuid4()
    storage = LocalStorage()
    rel = storage.save_bytes(
        user_id=owner_user_id,
        job_id=file_id,
        data=data,
        ext=normalized_ext,
        relative_name=f"catalog/covers/{file_id}.{normalized_ext}",
    )
    return to_public_files_url(rel)


def generate_and_store_creator_avatar(
    *,
    user_id: UUID,
    display_name: str,
    bio: str = "",
) -> tuple[str, str]:
    """返回 (public_url, prompt)。"""
    settings = get_settings()
    if not settings.catalog_cover_gen_enabled:
        raise CatalogCoverError(
            "COVER_GEN_DISABLED",
            "头像 AI 生成未启用，请设置 CATALOG_COVER_GEN_ENABLED=true",
            503,
        )
    client = WanxClient()
    if not client.enabled:
        raise CatalogCoverError(
            "WANX_NOT_CONFIGURED",
            "未配置 DASHSCOPE_API_KEY",
            503,
        )

    prompt = build_creator_avatar_prompt(display_name=display_name, bio=bio)
    try:
        png = client.generate_png(prompt=prompt)
    except WanxError as exc:
        raise CatalogCoverError(exc.code, exc.message, 502) from exc

    storage = LocalStorage()
    rel = storage.save_bytes(
        user_id=user_id,
        job_id=user_id,
        data=png,
        ext="png",
        relative_name=f"users/avatars/{user_id}.png",
    )
    return storage.public_url(rel), prompt
