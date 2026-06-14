from __future__ import annotations

from fastapi import HTTPException
from voice_platform.quota.exceptions import QuotaExceededError


def raise_quota_http(exc: QuotaExceededError) -> None:
    detail = exc.to_detail()
    raise HTTPException(status_code=402, detail=detail) from exc
