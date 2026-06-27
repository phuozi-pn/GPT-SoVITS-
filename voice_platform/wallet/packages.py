from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPackage:
    sku: str
    label: str
    token_amount: int
    price_cents: int
    hint: str


TOKEN_PACKAGES: tuple[TokenPackage, ...] = (
    TokenPackage(
        sku="starter",
        label="入门包",
        token_amount=50_000,
        price_cents=990,
        hint="约 5 万字配音",
    ),
    TokenPackage(
        sku="creator",
        label="创作包",
        token_amount=500_000,
        price_cents=4990,
        hint="独立创作者月度补充",
    ),
    TokenPackage(
        sku="studio",
        label="工作室包",
        token_amount=3_000_000,
        price_cents=19990,
        hint="短剧批量出片",
    ),
)


def get_package(sku: str) -> TokenPackage | None:
    for pkg in TOKEN_PACKAGES:
        if pkg.sku == sku:
            return pkg
    return None
