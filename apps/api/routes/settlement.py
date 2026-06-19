from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.settlement.service import SettlementService, SettlementServiceError
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from voice_platform.settlement.schemas import (
    AdminPayoutActionBody,
    PayoutRequestBody,
    PayoutRequestResponse,
    SellerLedgerEntry,
    SellerWalletResponse,
)

router = APIRouter()


@router.get("/seller/wallet", response_model=SellerWalletResponse)
def get_seller_wallet(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> SellerWalletResponse:
    return SettlementService(session).get_wallet(user_id)


@router.get("/seller/ledger", response_model=list[SellerLedgerEntry])
def list_seller_ledger(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[SellerLedgerEntry]:
    return SettlementService(session).list_ledger(user_id, limit=limit)


@router.post("/seller/payouts", response_model=PayoutRequestResponse, status_code=201)
def request_payout(
    body: PayoutRequestBody,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PayoutRequestResponse:
    try:
        return SettlementService(session).request_payout(user_id, amount_cents=body.amount_cents)
    except SettlementServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/payouts", response_model=list[PayoutRequestResponse])
def list_admin_payouts(
    status: str | None = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[PayoutRequestResponse]:
    return SettlementService(session).list_payouts(status=status, limit=limit)


@router.post("/admin/payouts/{payout_id}/approve", response_model=PayoutRequestResponse)
def approve_payout(
    payout_id: UUID,
    body: AdminPayoutActionBody | None = None,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> PayoutRequestResponse:
    try:
        return SettlementService(session).approve_payout(
            payout_id,
            admin_user_id=admin_id,
            note=body.note if body else None,
        )
    except SettlementServiceError as exc:
        raise_domain_http(exc)


@router.post("/admin/payouts/{payout_id}/reject", response_model=PayoutRequestResponse)
def reject_payout(
    payout_id: UUID,
    body: AdminPayoutActionBody | None = None,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> PayoutRequestResponse:
    try:
        return SettlementService(session).reject_payout(
            payout_id,
            admin_user_id=admin_id,
            note=body.note if body else None,
        )
    except SettlementServiceError as exc:
        raise_domain_http(exc)
