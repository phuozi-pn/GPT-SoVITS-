"""User TTS Token wallet — mock purchase & ledger."""

from __future__ import annotations

from uuid import UUID

from voice_platform.wallet.packages import TOKEN_PACKAGES, get_package
from voice_platform.wallet.repository import UserWalletRepository
from voice_platform.wallet.schemas import (
    TokenPackageResponse,
    UserWalletResponse,
    WalletLedgerEntry,
    WalletPurchaseResponse,
)


class WalletServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class WalletService:
    def __init__(self, session) -> None:
        self._session = session
        self._repo = UserWalletRepository(session)

    def list_packages(self) -> list[TokenPackageResponse]:
        return [
            TokenPackageResponse(
                sku=pkg.sku,
                label=pkg.label,
                token_amount=pkg.token_amount,
                price_cents=pkg.price_cents,
                hint=pkg.hint,
                mock_payment=True,
            )
            for pkg in TOKEN_PACKAGES
        ]

    def get_wallet(self, user_id: UUID) -> UserWalletResponse:
        w = self._repo.get_wallet(user_id)
        return UserWalletResponse(
            user_id=w.user_id,
            token_balance=int(w.token_balance),
            total_purchased_tokens=int(w.total_purchased_tokens),
        )

    def list_ledger(self, user_id: UUID, *, limit: int = 50) -> list[WalletLedgerEntry]:
        rows = self._repo.list_ledger(user_id, limit=limit)
        return [
            WalletLedgerEntry(
                entry_id=r.id,
                kind=r.kind,
                token_delta=int(r.token_delta),
                balance_after=int(r.balance_after),
                job_id=r.job_id,
                package_sku=r.package_sku,
                note=r.note,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def purchase(self, user_id: UUID, *, package_sku: str) -> WalletPurchaseResponse:
        pkg = get_package(package_sku)
        if not pkg:
            raise WalletServiceError("PACKAGE_NOT_FOUND", "Token 套餐不存在", 404)
        entry = self._repo.credit_purchase(
            user_id=user_id,
            package_sku=pkg.sku,
            token_amount=pkg.token_amount,
            note=f"Mock purchase · {pkg.label}",
        )
        return WalletPurchaseResponse(
            package_sku=pkg.sku,
            tokens_granted=pkg.token_amount,
            token_balance=int(entry.balance_after),
            mock_payment=True,
        )
