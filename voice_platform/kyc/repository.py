from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from voice_platform.kyc.models import KycAuditLogRow


class KycAuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        *,
        user_id: UUID,
        action: str,
        status: str,
        provider: str = "mock",
        message: str | None = None,
        real_name_masked: str | None = None,
        id_number_last4: str | None = None,
        id_number_hash: str | None = None,
    ) -> KycAuditLogRow:
        row = KycAuditLogRow(
            user_id=user_id,
            action=action,
            status=status,
            provider=provider,
            message=message,
            real_name_masked=real_name_masked,
            id_number_last4=id_number_last4,
            id_number_hash=id_number_hash,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_for_user(self, user_id: UUID, *, limit: int = 20) -> list[KycAuditLogRow]:
        stmt = (
            select(KycAuditLogRow)
            .where(KycAuditLogRow.user_id == user_id)
            .order_by(desc(KycAuditLogRow.created_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())
