"""KYC provider interface (Phase 5 — REQ-002)."""

from __future__ import annotations

from uuid import UUID

from dataclasses import dataclass


@dataclass(frozen=True)
class KycSubmitResult:
    verified: bool
    status: str
    provider: str
    message: str
    external_ref: str | None = None


class KycProvider:
    name: str = "base"

    def submit(
        self,
        *,
        real_name: str,
        id_number: str,
        id_number_hash: str,
        user_id: UUID | None = None,
    ) -> KycSubmitResult:
        raise NotImplementedError


class KycProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)
