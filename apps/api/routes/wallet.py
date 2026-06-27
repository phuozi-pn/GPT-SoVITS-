from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.wallet.service import WalletService, WalletServiceError
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from voice_platform.wallet.schemas import (
    TokenPackageResponse,
    UserWalletResponse,
    WalletLedgerEntry,
    WalletPurchaseRequest,
    WalletPurchaseResponse,
)

router = APIRouter()


@router.get("/wallet", response_model=UserWalletResponse)
def get_user_wallet(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> UserWalletResponse:
    return WalletService(session).get_wallet(user_id)


@router.get("/wallet/packages", response_model=list[TokenPackageResponse])
def list_token_packages(
    session: Session = Depends(get_session),
) -> list[TokenPackageResponse]:
    return WalletService(session).list_packages()


@router.get("/wallet/ledger", response_model=list[WalletLedgerEntry])
def list_wallet_ledger(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[WalletLedgerEntry]:
    return WalletService(session).list_ledger(user_id, limit=limit)


@router.post("/wallet/purchase", response_model=WalletPurchaseResponse, status_code=201)
def purchase_tokens(
    body: WalletPurchaseRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> WalletPurchaseResponse:
    try:
        return WalletService(session).purchase(user_id, package_sku=body.package_sku)
    except WalletServiceError as exc:
        raise_domain_http(exc)
