from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from voice_platform.marketplace.models import (
    MarketplaceInviteCodeRow,
    MarketplaceInviteRedemptionRow,
    MarketplaceWaitlistRow,
)


class MarketplaceInviteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def has_active_invite(self, user_id: UUID) -> bool:
        row = self._session.scalar(
            select(MarketplaceInviteRedemptionRow).where(
                MarketplaceInviteRedemptionRow.user_id == user_id
            )
        )
        return row is not None

    def get_redemption(self, user_id: UUID) -> MarketplaceInviteRedemptionRow | None:
        return self._session.scalar(
            select(MarketplaceInviteRedemptionRow).where(
                MarketplaceInviteRedemptionRow.user_id == user_id
            )
        )

    def get_waitlist(self, user_id: UUID) -> MarketplaceWaitlistRow | None:
        return self._session.scalar(
            select(MarketplaceWaitlistRow).where(MarketplaceWaitlistRow.user_id == user_id)
        )

    def join_waitlist(
        self,
        *,
        user_id: UUID,
        contact: str,
        note: str,
    ) -> MarketplaceWaitlistRow:
        existing = self.get_waitlist(user_id)
        if existing:
            existing.contact = contact
            existing.note = note
            self._session.commit()
            self._session.refresh(existing)
            return existing
        row = MarketplaceWaitlistRow(
            id=uuid4(),
            user_id=user_id,
            contact=contact,
            note=note,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get_code(self, code: str) -> MarketplaceInviteCodeRow | None:
        normalized = code.strip().upper()
        return self._session.scalar(
            select(MarketplaceInviteCodeRow).where(MarketplaceInviteCodeRow.code == normalized)
        )

    def redeem_code(self, *, user_id: UUID, code: str) -> MarketplaceInviteRedemptionRow:
        if self.has_active_invite(user_id):
            existing = self._session.scalar(
                select(MarketplaceInviteRedemptionRow).where(
                    MarketplaceInviteRedemptionRow.user_id == user_id
                )
            )
            assert existing is not None
            return existing

        row = self.get_code(code)
        if not row:
            raise ValueError("INVALID_CODE")
        if row.revoked_at is not None:
            raise ValueError("CODE_REVOKED")
        if row.expires_at and row.expires_at < datetime.now(timezone.utc):
            raise ValueError("CODE_EXPIRED")
        if row.used_count >= row.max_uses:
            raise ValueError("CODE_EXHAUSTED")

        redemption = MarketplaceInviteRedemptionRow(
            id=uuid4(),
            invite_code_id=row.id,
            user_id=user_id,
        )
        row.used_count += 1
        self._session.add(redemption)
        self._session.commit()
        self._session.refresh(redemption)
        return redemption

    def create_code(
        self,
        *,
        code: str,
        max_uses: int,
        note: str,
        created_by: UUID | None,
        expires_in_days: int | None,
    ) -> MarketplaceInviteCodeRow:
        normalized = code.strip().upper()
        if self.get_code(normalized):
            raise ValueError("CODE_EXISTS")
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        row = MarketplaceInviteCodeRow(
            id=uuid4(),
            code=normalized,
            max_uses=max_uses,
            note=note,
            created_by=created_by,
            expires_at=expires_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_codes(self, *, limit: int = 50) -> list[MarketplaceInviteCodeRow]:
        return list(
            self._session.scalars(
                select(MarketplaceInviteCodeRow)
                .order_by(MarketplaceInviteCodeRow.created_at.desc())
                .limit(limit)
            )
        )

    def get_waitlist_by_id(self, waitlist_id: UUID) -> MarketplaceWaitlistRow | None:
        return self._session.get(MarketplaceWaitlistRow, waitlist_id)

    def list_waitlist_pending(self, *, limit: int = 50) -> list[MarketplaceWaitlistRow]:
        return list(
            self._session.scalars(
                select(MarketplaceWaitlistRow)
                .where(MarketplaceWaitlistRow.fulfilled_at.is_(None))
                .order_by(MarketplaceWaitlistRow.created_at.asc())
                .limit(limit)
            )
        )

    def mark_waitlist_fulfilled(
        self,
        row: MarketplaceWaitlistRow,
        *,
        invite_code_id: UUID,
    ) -> MarketplaceWaitlistRow:
        row.fulfilled_at = datetime.now(timezone.utc)
        row.issued_invite_code_id = invite_code_id
        self._session.commit()
        self._session.refresh(row)
        return row
