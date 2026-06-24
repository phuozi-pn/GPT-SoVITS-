"""Dev helper: mark a pending payment order as paid via internal webhook."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
SECRET = os.environ.get("PAYMENT_WEBHOOK_SECRET", "dev-payment-webhook-secret-change-me")


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm payment via platform webhook")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--provider-ref", required=True)
    parser.add_argument("--provider", default="alipay")
    args = parser.parse_args()

    body = json.dumps(
        {
            "order_id": args.order_id,
            "provider_ref": args.provider_ref,
            "status": "paid",
        }
    ).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    url = f"{BASE}/api/v1/payments/webhooks/{args.provider}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            content=body,
            headers={"X-Payment-Signature": sig, "Content-Type": "application/json"},
        )
    print(resp.status_code, resp.text)
    return 0 if resp.status_code < 400 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
