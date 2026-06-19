from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from voice_platform.developer.models import ApiKeyRow

DEFAULT_SCOPES = ["synthesis:write", "jobs:read"]
KEY_PREFIX = "vsk_"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_prefix, key_hash)."""
    suffix = secrets.token_hex(16)
    full = f"{KEY_PREFIX}{suffix}"
    return full, full[:12], hash_api_key(full)


class ApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, user_id: UUID, name: str, scopes: list[str] | None = None) -> tuple[ApiKeyRow, str]:
        full_key, prefix, key_hash = generate_api_key()
        row = ApiKeyRow(
            id=uuid4(),
            user_id=user_id,
            name=name.strip(),
            key_prefix=prefix,
            key_hash=key_hash,
            scopes_json=scopes or list(DEFAULT_SCOPES),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row, full_key

    def list_for_user(self, user_id: UUID) -> list[ApiKeyRow]:
        stmt = (
            select(ApiKeyRow)
            .where(ApiKeyRow.user_id == user_id)
            .order_by(desc(ApiKeyRow.created_at))
        )
        return list(self._session.scalars(stmt).all())

    def get(self, key_id: UUID) -> ApiKeyRow | None:
        return self._session.get(ApiKeyRow, key_id)

    def find_active_by_hash(self, key_hash: str) -> ApiKeyRow | None:
        stmt = select(ApiKeyRow).where(
            ApiKeyRow.key_hash == key_hash,
            ApiKeyRow.revoked_at.is_(None),
        )
        return self._session.scalars(stmt).first()

    def revoke(self, key_id: UUID, user_id: UUID) -> ApiKeyRow | None:
        row = self.get(key_id)
        if not row or row.user_id != user_id or row.revoked_at:
            return None
        row.revoked_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return row

    def touch_used(self, key_id: UUID) -> None:
        row = self.get(key_id)
        if row:
            row.last_used_at = datetime.now(timezone.utc)
            self._session.commit()
