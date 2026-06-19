"""REQ-030 API key management and validation."""

from __future__ import annotations

from uuid import UUID

from voice_platform.developer.repository import ApiKeyRepository, hash_api_key
from voice_platform.developer.schemas import ApiKeyCreatedResponse, ApiKeySummary


class DeveloperServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class DeveloperService:
    def __init__(self, session) -> None:
        self._repo = ApiKeyRepository(session)
        self._session = session

    def create_key(self, user_id: UUID, *, name: str) -> ApiKeyCreatedResponse:
        row, full_key = self._repo.create(user_id=user_id, name=name)
        return ApiKeyCreatedResponse(
            key_id=row.id,
            name=row.name,
            key_prefix=row.key_prefix,
            api_key=full_key,
            scopes=list(row.scopes_json or []),
            created_at=row.created_at,
        )

    def list_keys(self, user_id: UUID) -> list[ApiKeySummary]:
        return [
            ApiKeySummary(
                key_id=r.id,
                name=r.name,
                key_prefix=r.key_prefix,
                scopes=list(r.scopes_json or []),
                revoked=r.revoked_at is not None,
                last_used_at=r.last_used_at,
                created_at=r.created_at,
            )
            for r in self._repo.list_for_user(user_id)
        ]

    def revoke_key(self, user_id: UUID, key_id: UUID) -> ApiKeySummary:
        row = self._repo.revoke(key_id, user_id)
        if not row:
            raise DeveloperServiceError("API_KEY_NOT_FOUND", "API key not found", 404)
        return ApiKeySummary(
            key_id=row.id,
            name=row.name,
            key_prefix=row.key_prefix,
            scopes=list(row.scopes_json or []),
            revoked=True,
            last_used_at=row.last_used_at,
            created_at=row.created_at,
        )

    def resolve_user_from_key(self, raw_key: str) -> tuple[UUID, ApiKeyRow]:
        if not raw_key.startswith("vsk_"):
            raise DeveloperServiceError("INVALID_API_KEY", "Invalid API key format", 401)
        row = self._repo.find_active_by_hash(hash_api_key(raw_key))
        if not row:
            raise DeveloperServiceError("INVALID_API_KEY", "API key invalid or revoked", 401)
        self._repo.touch_used(row.id)
        return row.user_id, row

    def require_scope(self, row: ApiKeyRow, scope: str) -> None:
        scopes = list(row.scopes_json or [])
        if scope not in scopes:
            raise DeveloperServiceError(
                "API_KEY_SCOPE_DENIED",
                f"API key missing scope: {scope}",
                403,
            )
