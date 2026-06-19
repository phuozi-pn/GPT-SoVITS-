from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from voice_platform.settlement.models import PayoutRequestRow, SellerLedgerEntryRow, SellerWalletRow


class SettlementRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_wallet(self, user_id: UUID) -> SellerWalletRow:
        row = self._session.get(SellerWalletRow, user_id)
        if not row:
            row = SellerWalletRow(user_id=user_id)
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
        return row

    def has_ledger_for_order(self, payment_order_id: UUID) -> bool:
        stmt = select(SellerLedgerEntryRow.id).where(
            SellerLedgerEntryRow.payment_order_id == payment_order_id,
            SellerLedgerEntryRow.kind == "sale_credit",
        )
        return self._session.scalars(stmt).first() is not None

    def credit_sale(
        self,
        *,
        seller_user_id: UUID,
        payment_order_id: UUID,
        gross_cents: int,
        fee_cents: int,
        net_cents: int,
    ) -> SellerLedgerEntryRow:
        wallet = self.get_wallet(seller_user_id)
        wallet.balance_cents += net_cents
        wallet.total_earned_cents += net_cents
        wallet.updated_at = datetime.now(timezone.utc)
        entry = SellerLedgerEntryRow(
            id=uuid4(),
            seller_user_id=seller_user_id,
            payment_order_id=payment_order_id,
            kind="sale_credit",
            gross_cents=gross_cents,
            fee_cents=fee_cents,
            net_cents=net_cents,
            balance_after_cents=wallet.balance_cents,
            note="Voice catalog sale",
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return entry

    def list_ledger(self, seller_user_id: UUID, *, limit: int = 50) -> list[SellerLedgerEntryRow]:
        stmt = (
            select(SellerLedgerEntryRow)
            .where(SellerLedgerEntryRow.seller_user_id == seller_user_id)
            .order_by(desc(SellerLedgerEntryRow.created_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def create_payout_request(
        self, *, seller_user_id: UUID, amount_cents: int
    ) -> PayoutRequestRow:
        wallet = self.get_wallet(seller_user_id)
        if wallet.balance_cents < amount_cents:
            raise ValueError("insufficient balance")
        wallet.balance_cents -= amount_cents
        wallet.pending_payout_cents += amount_cents
        wallet.updated_at = datetime.now(timezone.utc)
        row = PayoutRequestRow(
            id=uuid4(),
            seller_user_id=seller_user_id,
            amount_cents=amount_cents,
            status="pending",
        )
        self._session.add(row)
        ledger = SellerLedgerEntryRow(
            id=uuid4(),
            seller_user_id=seller_user_id,
            kind="payout_hold",
            gross_cents=-amount_cents,
            fee_cents=0,
            net_cents=-amount_cents,
            balance_after_cents=wallet.balance_cents,
            note=f"Payout request {row.id}",
        )
        self._session.add(ledger)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get_payout(self, payout_id: UUID) -> PayoutRequestRow | None:
        return self._session.get(PayoutRequestRow, payout_id)

    def list_payouts(self, *, status: str | None = None, limit: int = 50) -> list[PayoutRequestRow]:
        stmt = select(PayoutRequestRow).order_by(desc(PayoutRequestRow.created_at)).limit(limit)
        if status:
            stmt = stmt.where(PayoutRequestRow.status == status)
        return list(self._session.scalars(stmt).all())

    def approve_payout(
        self, payout_id: UUID, *, admin_user_id: UUID, note: str | None
    ) -> PayoutRequestRow | None:
        row = self.get_payout(payout_id)
        if not row or row.status != "pending":
            return None
        wallet = self.get_wallet(row.seller_user_id)
        wallet.pending_payout_cents = max(0, wallet.pending_payout_cents - row.amount_cents)
        wallet.updated_at = datetime.now(timezone.utc)
        row.status = "paid"
        row.processed_by = admin_user_id
        row.processed_at = datetime.now(timezone.utc)
        row.note = note
        ledger = SellerLedgerEntryRow(
            id=uuid4(),
            seller_user_id=row.seller_user_id,
            kind="payout_paid",
            gross_cents=-row.amount_cents,
            fee_cents=0,
            net_cents=-row.amount_cents,
            balance_after_cents=wallet.balance_cents,
            note=note or "Payout approved (mock transfer)",
        )
        self._session.add(ledger)
        self._session.commit()
        self._session.refresh(row)
        return row

    def reject_payout(
        self, payout_id: UUID, *, admin_user_id: UUID, note: str | None
    ) -> PayoutRequestRow | None:
        row = self.get_payout(payout_id)
        if not row or row.status != "pending":
            return None
        wallet = self.get_wallet(row.seller_user_id)
        wallet.balance_cents += row.amount_cents
        wallet.pending_payout_cents = max(0, wallet.pending_payout_cents - row.amount_cents)
        wallet.updated_at = datetime.now(timezone.utc)
        row.status = "rejected"
        row.processed_by = admin_user_id
        row.processed_at = datetime.now(timezone.utc)
        row.note = note
        ledger = SellerLedgerEntryRow(
            id=uuid4(),
            seller_user_id=row.seller_user_id,
            kind="payout_rejected",
            gross_cents=row.amount_cents,
            fee_cents=0,
            net_cents=row.amount_cents,
            balance_after_cents=wallet.balance_cents,
            note=note or "Payout rejected — balance restored",
        )
        self._session.add(ledger)
        self._session.commit()
        self._session.refresh(row)
        return row
