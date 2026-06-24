"""Alipay sandbox: precreate only — prints QR URL for manual scan."""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
BUYER = os.environ.get("GRANTEE_ID", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CATALOG_ID = os.environ.get(
    "SMOKE_CATALOG_ID", "22222222-2222-2222-2222-222222222222"
)


def main() -> int:
    provider = os.environ.get("PAYMENT_PROVIDER", "")
    if provider and provider != "alipay":
        print(f"PAYMENT_PROVIDER={provider}, expected alipay for this script", file=sys.stderr)
        return 1

    with httpx.Client(
        base_url=BASE,
        headers={"X-User-Id": BUYER},
        timeout=60.0,
    ) as client:
        checkout = client.post(f"/api/v1/catalog/voices/{CATALOG_ID}/checkout")
        print("checkout", checkout.status_code)
        if checkout.status_code >= 400:
            print(checkout.text, file=sys.stderr)
            return 1
        body = checkout.json()
        print("order_id:", body.get("order_id"))
        print("provider_ref:", body.get("provider_ref"))
        print("status:", body.get("status"))
        qr = body.get("qr_code_url")
        if not qr:
            print("No qr_code_url — check ALIPAY_* env and PAYMENT_NOTIFY_BASE_URL", file=sys.stderr)
            return 1
        print("\n=== Scan with Alipay Sandbox App ===\n")
        print(qr)
        print("\nAfter payment, confirm order via webhook (see docs/architecture/2026-06-22-alipay-sandbox-沙箱联调.md)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
