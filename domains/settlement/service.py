"""REQ-028 seller wallet, ledger, and mock payouts."""

from __future__ import annotations

from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.job.models import PaymentOrderRow
from voice_platform.settlement.repository import SettlementRepository
from voice_platform.settlement.schemas import (
    PayoutRequestResponse,
    SellerLedgerEntry,
    SellerWalletResponse,
)


class SettlementServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class SettlementService:
    def __init__(self, session) -> None:
        self._session = session
        self._repo = SettlementRepository(session)
        self._settings = get_settings()

    def credit_from_payment_order(self, order: PaymentOrderRow) -> None:
        if order.status != "paid" or order.amount_cents <= 0:
            return
        if self._repo.has_ledger_for_order(order.id):
            return
        fee = round(order.amount_cents * self._settings.settlement_platform_fee_bps / 10000)
        net = order.amount_cents - fee
        self._repo.credit_sale(
            seller_user_id=order.seller_user_id,
            payment_order_id=order.id,
            gross_cents=order.amount_cents,
            fee_cents=fee,
            net_cents=net,
        )

    def get_wallet(self, seller_user_id: UUID) -> SellerWalletResponse:
        w = self._repo.get_wallet(seller_user_id)
        return SellerWalletResponse(
            seller_user_id=w.user_id,
            balance_cents=int(w.balance_cents),
            pending_payout_cents=int(w.pending_payout_cents),
            total_earned_cents=int(w.total_earned_cents),
            platform_fee_bps=self._settings.settlement_platform_fee_bps,
            min_payout_cents=self._settings.settlement_min_payout_cents,
        )

    def list_ledger(self, seller_user_id: UUID, *, limit: int = 50) -> list[SellerLedgerEntry]:
        rows = self._repo.list_ledger(seller_user_id, limit=limit)
        return [
            SellerLedgerEntry(
                entry_id=r.id,
                kind=r.kind,
                gross_cents=r.gross_cents,
                fee_cents=r.fee_cents,
                net_cents=r.net_cents,
                balance_after_cents=int(r.balance_after_cents),
                payment_order_id=r.payment_order_id,
                note=r.note,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def request_payout(self, seller_user_id: UUID, *, amount_cents: int) -> PayoutRequestResponse:
        if amount_cents < self._settings.settlement_min_payout_cents:
            raise SettlementServiceError(
                "PAYOUT_BELOW_MINIMUM",
                f"Minimum payout is {self._settings.settlement_min_payout_cents} cents",
                400,
            )
        try:
            row = self._repo.create_payout_request(
                seller_user_id=seller_user_id,
                amount_cents=amount_cents,
            )
        except ValueError as exc:
            raise SettlementServiceError("INSUFFICIENT_BALANCE", str(exc), 400) from exc
        return self._payout_response(row)

    def list_payouts(self, *, status: str | None = None, limit: int = 50) -> list[PayoutRequestResponse]:
        return [self._payout_response(r) for r in self._repo.list_payouts(status=status, limit=limit)]

    def approve_payout(
        self, payout_id: UUID, *, admin_user_id: UUID, note: str | None = None
    ) -> PayoutRequestResponse:
        row = self._repo.approve_payout(payout_id, admin_user_id=admin_user_id, note=note)
        if not row:
            raise SettlementServiceError("PAYOUT_NOT_FOUND", "Pending payout not found", 404)
        return self._payout_response(row)

    def reject_payout(
        self, payout_id: UUID, *, admin_user_id: UUID, note: str | None = None
    ) -> PayoutRequestResponse:
        row = self._repo.reject_payout(payout_id, admin_user_id=admin_user_id, note=note)
        if not row:
            raise SettlementServiceError("PAYOUT_NOT_FOUND", "Pending payout not found", 404)
        return self._payout_response(row)

    def _payout_response(self, row) -> PayoutRequestResponse:
        return PayoutRequestResponse(
            payout_id=row.id,
            seller_user_id=row.seller_user_id,
            amount_cents=row.amount_cents,
            status=row.status,
            note=row.note,
            created_at=row.created_at,
            processed_at=row.processed_at,
        )
