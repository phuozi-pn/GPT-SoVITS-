from __future__ import annotations

from uuid import UUID, uuid4

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from voice_platform.auth.identifiers import normalize_email
from voice_platform.auth.models import UserRow


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> UserRow | None:
        return self._session.get(UserRow, user_id)

    def list_by_verified(self, *, verified: bool, limit: int = 50) -> list[UserRow]:
        stmt = (
            select(UserRow)
            .where(UserRow.verified == verified)
            .order_by(desc(UserRow.created_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_by_email(self, email: str) -> UserRow | None:
        normalized = normalize_email(email)
        return self._session.scalars(select(UserRow).where(UserRow.email == normalized)).first()

    def get_or_create_by_email(self, email: str) -> UserRow:
        normalized = normalize_email(email)
        row = self.get_by_email(normalized)
        if row:
            return row
        row = UserRow(id=uuid4(), phone=None, email=normalized, status="active", verified=False)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get_by_phone(self, phone: str) -> UserRow | None:
        return self._session.scalars(select(UserRow).where(UserRow.phone == phone)).first()

    def get_or_create(self, phone: str) -> UserRow:
        row = self.get_by_phone(phone)
        if row:
            return row
        row = UserRow(id=uuid4(), phone=phone, status="active", verified=False)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def ensure_dev_user(self, user_id: UUID) -> UserRow:
        """
        In DEV_SKIP_AUTH mode we allow requests with X-User-Id but still need a backing
        user row for FK constraints (e.g. messages, downloads).
        """
        row = self.get_by_id(user_id)
        if row:
            return row
        phone = f"dev-{str(user_id).split('-')[0]}"
        row = UserRow(id=user_id, phone=phone[:16], status="active", verified=False)
        self._session.add(row)
        try:
            self._session.commit()
            self._session.refresh(row)
            return row
        except IntegrityError:
            self._session.rollback()
            row = self.get_by_id(user_id)
            if row:
                return row
            raise

    def ensure_system_user(self, user_id: UUID) -> UserRow:
        row = self.get_by_id(user_id)
        if row:
            return row
        # phone has a 16-char limit; keep deterministic and unique.
        row = UserRow(id=user_id, phone="system", status="active", verified=False)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def set_verified(
        self,
        user_id: UUID,
        *,
        verified: bool,
        id_number_hash: str | None = None,
        clear_id_hash: bool = False,
    ) -> UserRow | None:
        row = self.get_by_id(user_id)
        if not row:
            return None
        row.verified = verified
        row.verified_at = datetime.now(timezone.utc) if verified else None
        if clear_id_hash:
            row.id_number_hash = None
        elif id_number_hash is not None:
            row.id_number_hash = id_number_hash
        self._session.commit()
        self._session.refresh(row)
        return row
