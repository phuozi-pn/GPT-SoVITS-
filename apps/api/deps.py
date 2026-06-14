from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from voice_platform.auth.jwt import TokenError, decode_access_token
from voice_platform.config import get_settings


def get_trace_id(request: Request) -> str:
    return request.headers.get("X-Trace-Id", request.headers.get("X-Request-Id", "dev-trace"))


def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UUID:
    settings = get_settings()

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_REQUIRED", "message": "Invalid Authorization header"},
            )
        try:
            return decode_access_token(token)
        except TokenError as exc:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_REQUIRED", "message": str(exc)},
            ) from exc

    if settings.dev_skip_auth:
        raw = x_user_id or settings.dev_user_id
        try:
            return UUID(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_REQUIRED", "message": "Invalid user id"},
            ) from exc

    raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Login required"})
