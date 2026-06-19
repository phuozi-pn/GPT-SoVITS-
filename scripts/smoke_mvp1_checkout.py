"""Smoke: async checkout + mock confirm + webhook."""

from __future__ import annotations

import json
import os
import sys

import httpx

from voice_platform.payment.webhook import sign_webhook_payload

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
OWNER = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
BUYER = os.environ.get("GRANTEE_ID", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ADMIN = os.environ.get("ADMIN_USER_ID", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PRICE_CENTS = int(os.environ.get("SMOKE_PRICE_CENTS", "9900"))
WEBHOOK_SECRET = os.environ.get(
    "PAYMENT_WEBHOOK_SECRET", "dev-payment-webhook-secret-change-me"
)


def _client(user_id: str | None = None) -> httpx.Client:
    headers: dict[str, str] = {}
    if user_id:
        headers["X-User-Id"] = user_id
    return httpx.Client(base_url=BASE, headers=headers, timeout=60.0)


def main() -> int:
    catalog_id: str | None = None

    with _client(OWNER) as owner:
        versions = owner.get("/api/v1/voice-versions")
        versions.raise_for_status()
        owned = [v for v in versions.json() if not v.get("granted")]
        if not owned:
            raise RuntimeError("Owner has no voice versions")
        version_id = owned[0]["voice_version_id"]

        pub = owner.post(
            "/api/v1/catalog/voices",
            json={
                "voice_version_id": version_id,
                "title": "Smoke·结账音色",
                "description": "smoke_mvp1_checkout.py",
                "tags": ["smoke", "checkout"],
                "license_type": "commercial_standard",
                "price_cents": PRICE_CENTS,
                "billing_unit": "per_1k_chars",
                "included_chars": 50000,
            },
        )
        pub.raise_for_status()
        catalog_id = pub.json()["catalog_id"]

    with _client(ADMIN) as admin:
        admin.post(f"/api/v1/catalog/voices/{catalog_id}/approve").raise_for_status()

    with _client(BUYER) as buyer:
        checkout = buyer.post(f"/api/v1/catalog/voices/{catalog_id}/checkout")
        print("checkout", checkout.status_code, checkout.json().get("status"))
        checkout.raise_for_status()
        body = checkout.json()
        if body["status"] != "pending":
            print("Expected pending checkout", file=sys.stderr)
            return 1
        order_id = body["order_id"]
        provider_ref = body["provider_ref"]

        confirm = buyer.post(f"/api/v1/payments/orders/{order_id}/mock-confirm")
        print("mock-confirm", confirm.status_code)
        confirm.raise_for_status()
        auth_id = confirm.json()["authorization_id"]

        catalog = buyer.get("/api/v1/catalog/voices")
        catalog.raise_for_status()
        entry = next(e for e in catalog.json() if e["catalog_id"] == catalog_id)
        if not entry.get("can_use"):
            print("Expected can_use after checkout", file=sys.stderr)
            return 1

    payload = json.dumps(
        {"order_id": order_id, "provider_ref": provider_ref, "status": "paid"}
    ).encode()
    sig = sign_webhook_payload(WEBHOOK_SECRET, payload)
    with httpx.Client(base_url=BASE, timeout=30.0) as public:
        wh = public.post(
            "/api/v1/payments/webhooks/mock",
            content=payload,
            headers={"X-Payment-Signature": sig, "Content-Type": "application/json"},
        )
        print("webhook replay", wh.status_code, wh.json().get("status"))
        wh.raise_for_status()

    with httpx.Client(base_url=BASE, timeout=30.0) as public:
        verify = public.get(f"/api/v1/authorizations/{auth_id}/verify")
        verify.raise_for_status()
        if not verify.json().get("valid"):
            print("Authorization not valid", file=sys.stderr)
            return 1

    print("Checkout + mock confirm + webhook smoke OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
