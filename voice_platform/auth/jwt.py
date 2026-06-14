from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from voice_platform.config import get_settings


class TokenError(Exception):
    pass


def create_access_token(*, user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token") from exc
    sub = payload.get("sub")
    if not sub:
        raise TokenError("Missing subject")
    try:
        return UUID(sub)
    except ValueError as exc:
        raise TokenError("Invalid subject") from exc
