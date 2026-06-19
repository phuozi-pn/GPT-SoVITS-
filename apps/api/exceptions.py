"""Shared HTTP exception conversion helpers for route handlers.

These utilities eliminate the repetitive pattern of wrapping domain-level
service exceptions into FastAPI HTTPException across route files.

Domain services raise typed exceptions (e.g. MarketplaceServiceError,
LicensingServiceError, etc.) that all follow the same convention:
    exc.code       -> error code string
    exc.message    -> human-readable message
    exc.http_status -> corresponding HTTP status code

Route handlers should use these helpers instead of writing the same
try/except/raise pattern in every endpoint.
"""

from __future__ import annotations

from fastapi import HTTPException


def raise_domain_http(exc: Exception) -> None:
    """Convert a domain service exception to an HTTPException.

    Expects the exception to have .code, .message, and .http_status attributes.
    If the exception has a .details dict, it is merged into the response detail.
    """
    code = getattr(exc, "code", "INTERNAL_ERROR")
    message = getattr(exc, "message", str(exc))
    http_status = getattr(exc, "http_status", 500)
    payload: dict = {"code": code, "message": message}
    extra_details = getattr(exc, "details", None)
    if extra_details:
        payload["details"] = extra_details
    raise HTTPException(
        status_code=http_status,
        detail=payload,
    ) from exc


def parse_tag_query(*, tag: str | None, tags: str | None) -> list[str]:
    """Parse and deduplicate tag query parameters from URL.

    Handles both single 'tag' and comma-separated 'tags' params,
    including full-width commas. Returns at most 10 unique tags.
    """
    out: list[str] = []
    if tags:
        out.extend(t.strip() for t in tags.replace("\uff0c", ",").split(",") if t.strip())
    if tag and tag.strip():
        out.append(tag.strip())
    seen: set[str] = set()
    unique: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:10]
