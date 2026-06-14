from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from voice_platform.auth.models import UserRow


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> UserRow | None:
        return self._session.get(UserRow, user_id)

    def get_by_phone(self, phone: str) -> UserRow | None:
        return self._session.scalars(select(UserRow).where(UserRow.phone == phone)).first()

    def get_or_create(self, phone: str) -> UserRow:
        row = self.get_by_phone(phone)
        if row:
            return row
        row = UserRow(id=uuid4(), phone=phone, status="active")
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row
