from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from voice_platform.wallet.models import UserWalletLedgerRow, UserWalletRow


class InsufficientWalletBalanceError(Exception):
    pass


class UserWalletRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_wallet(self, user_id: UUID) -> UserWalletRow:
        row = self._session.get(UserWalletRow, user_id)
        if not row:
            row = UserWalletRow(user_id=user_id)
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
        return row

    def get_balance(self, user_id: UUID) -> int:
        return int(self.get_wallet(user_id).token_balance)

    def credit_purchase(
        self,
        *,
        user_id: UUID,
        package_sku: str,
        token_amount: int,
        note: str | None = None,
    ) -> UserWalletLedgerRow:
        wallet = self.get_wallet(user_id)
        wallet.token_balance += token_amount
        wallet.total_purchased_tokens += token_amount
        wallet.updated_at = datetime.now(timezone.utc)
        entry = UserWalletLedgerRow(
            id=uuid4(),
            user_id=user_id,
            kind="purchase",
            token_delta=token_amount,
            balance_after=wallet.token_balance,
            package_sku=package_sku,
            note=note or f"Mock purchase {package_sku}",
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return entry

    def debit_synthesis(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        token_amount: int,
    ) -> UserWalletLedgerRow | None:
        if token_amount <= 0:
            return None
        wallet = self.get_wallet(user_id)
        if wallet.token_balance < token_amount:
            raise InsufficientWalletBalanceError()
        wallet.token_balance -= token_amount
        wallet.updated_at = datetime.now(timezone.utc)
        entry = UserWalletLedgerRow(
            id=uuid4(),
            user_id=user_id,
            kind="synthesis_debit",
            token_delta=-token_amount,
            balance_after=wallet.token_balance,
            job_id=job_id,
            note="TTS synthesis overflow from monthly quota",
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return entry

    def list_ledger(self, user_id: UUID, *, limit: int = 50) -> list[UserWalletLedgerRow]:
        stmt = (
            select(UserWalletLedgerRow)
            .where(UserWalletLedgerRow.user_id == user_id)
            .order_by(desc(UserWalletLedgerRow.created_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())
