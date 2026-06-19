"""Smoke: paid catalog publish → approve → purchase → certificate → verify → takedown."""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
OWNER = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
BUYER = os.environ.get("GRANTEE_ID", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ADMIN = os.environ.get("ADMIN_USER_ID", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PRICE_CENTS = int(os.environ.get("SMOKE_PRICE_CENTS", "9900"))


def _client(user_id: str | None = None) -> httpx.Client:
    headers: dict[str, str] = {}
    if user_id:
        headers["X-User-Id"] = user_id
    return httpx.Client(base_url=BASE, headers=headers, timeout=60.0)


def _pick_version(client: httpx.Client) -> str:
    versions = client.get("/api/v1/voice-versions")
    versions.raise_for_status()
    owned = [v for v in versions.json() if not v.get("granted")]
    if not owned:
        raise RuntimeError("Owner has no voice versions — import 004 in library first")
    return owned[0]["voice_version_id"]


def main() -> int:
    catalog_id: str | None = None
    auth_id: str | None = None

    with _client(OWNER) as owner:
        version_id = _pick_version(owner)
        print("voice_version_id", version_id)

        pub = owner.post(
            "/api/v1/catalog/voices",
            json={
                "voice_version_id": version_id,
                "title": "Smoke·付费音色",
                "description": "smoke_mvp1_purchase.py",
                "tags": ["smoke", "paid"],
                "featured": False,
                "demo_text": "方源，你给我出来！",
                "license_type": "commercial_standard",
                "price_cents": PRICE_CENTS,
                "billing_unit": "per_1k_chars",
                "included_chars": 50000,
                "prohibited_domains": ["political"],
            },
        )
        print("POST /catalog/voices", pub.status_code)
        pub.raise_for_status()
        catalog_id = pub.json()["catalog_id"]
        print("catalog_id", catalog_id)

    with _client(ADMIN) as admin:
        approve = admin.post(f"/api/v1/catalog/voices/{catalog_id}/approve")
        print("POST approve", approve.status_code)
        approve.raise_for_status()

    with _client(BUYER) as buyer:
        catalog = buyer.get("/api/v1/catalog/voices")
        catalog.raise_for_status()
        entry = next((e for e in catalog.json() if e["catalog_id"] == catalog_id), None)
        if not entry:
            print("Published entry not in catalog list", file=sys.stderr)
            return 1
        print("before purchase can_use=", entry.get("can_use"), "price=", entry.get("price_cents"))
        if entry.get("can_use"):
            print("Expected can_use=false before purchase for paid voice", file=sys.stderr)
            return 1

        purchase = buyer.post(f"/api/v1/catalog/voices/{catalog_id}/purchase")
        print("POST purchase", purchase.status_code, purchase.json().get("payment_ref"))
        purchase.raise_for_status()
        auth_id = purchase.json()["authorization_id"]

        auths = buyer.get("/api/v1/authorizations")
        auths.raise_for_status()
        if not any(a["authorization_id"] == auth_id for a in auths.json()):
            print("Authorization not listed for buyer", file=sys.stderr)
            return 1

        cert = buyer.get(f"/api/v1/authorizations/{auth_id}/certificate")
        cert.raise_for_status()
        if not cert.json().get("signature"):
            print("Certificate missing signature", file=sys.stderr)
            return 1
        print("certificate OK", cert.json()["voice_title"])

        pdf = buyer.get(f"/api/v1/authorizations/{auth_id}/certificate.pdf")
        pdf.raise_for_status()
        if pdf.headers.get("content-type") != "application/pdf":
            print("Expected application/pdf content-type", file=sys.stderr)
            return 1
        if pdf.content[:4] != b"%PDF":
            print("PDF response missing %PDF header", file=sys.stderr)
            return 1
        print("certificate.pdf OK", len(pdf.content), "bytes")

        catalog2 = buyer.get("/api/v1/catalog/voices")
        catalog2.raise_for_status()
        entry2 = next(e for e in catalog2.json() if e["catalog_id"] == catalog_id)
        print("after purchase can_use=", entry2.get("can_use"), "purchased=", entry2.get("purchased"))
        if not entry2.get("can_use"):
            print("Expected can_use=true after purchase", file=sys.stderr)
            return 1

    with httpx.Client(base_url=BASE, timeout=30.0) as public:
        verify = public.get(f"/api/v1/authorizations/{auth_id}/verify")
        verify.raise_for_status()
        body = verify.json()
        print("verify", body.get("valid"), body.get("message"))
        if not body.get("valid"):
            print("Verify expected valid=true", file=sys.stderr)
            return 1

    with _client(BUYER) as buyer:
        complaint = buyer.post(
            "/api/v1/complaints",
            json={
                "catalog_id": catalog_id,
                "description": "Smoke test complaint for takedown workflow validation",
            },
        )
        complaint.raise_for_status()
        complaint_id = complaint.json()["complaint_id"]
        print("complaint_id", complaint_id)

    with _client(ADMIN) as admin:
        takedown = admin.post(f"/api/v1/admin/complaints/{complaint_id}/takedown")
        print("POST takedown", takedown.status_code)
        takedown.raise_for_status()

    with httpx.Client(base_url=BASE, timeout=30.0) as public:
        verify2 = public.get(f"/api/v1/authorizations/{auth_id}/verify")
        verify2.raise_for_status()
        body2 = verify2.json()
        print("verify after takedown valid=", body2.get("valid"), "status=", body2.get("status"))
        if body2.get("valid"):
            print("Expected valid=false after takedown revoke", file=sys.stderr)
            return 1

    print("MVP+1 purchase + certificate + PDF + takedown smoke OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
