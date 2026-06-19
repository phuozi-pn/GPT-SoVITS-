"""Smoke: KYC gate before training (REQ-002)."""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
OWNER = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
VOICE = os.environ.get("SMOKE_VOICE_ID", "11111111-1111-1111-1111-111111111100")
ADULT_ID = os.environ.get("SMOKE_KYC_ID", "110101199001011234")


def _client(user_id: str) -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={"X-User-Id": user_id}, timeout=60.0)


def main() -> int:
    with _client(OWNER) as owner:
        status = owner.get("/api/v1/kyc/status")
        status.raise_for_status()
        body = status.json()
        print("kyc verified=", body.get("verified"), "required=", body.get("required"))

        train = owner.post(
            f"/api/v1/voices/{VOICE}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
        print("train before kyc", train.status_code, train.json().get("detail", {}).get("code"))
        if body.get("required") and not body.get("verified"):
            if train.status_code != 403 or train.json().get("detail", {}).get("code") != "KYC_REQUIRED":
                print("Expected KYC_REQUIRED before verification", file=sys.stderr)
                return 1

            submit = owner.post(
                "/api/v1/kyc/submit",
                json={"real_name": "测试用户", "id_number": ADULT_ID},
            )
            print("kyc submit", submit.status_code, submit.json().get("message"))
            submit.raise_for_status()
            if not submit.json().get("verified"):
                print("Expected verified=true after mock submit", file=sys.stderr)
                return 1

            status2 = owner.get("/api/v1/kyc/status")
            status2.raise_for_status()
            if not status2.json().get("verified"):
                print("Status still unverified", file=sys.stderr)
                return 1

            train2 = owner.post(
                f"/api/v1/voices/{VOICE}/train",
                json={"model_tag": "gsv-v2pro-20250606"},
            )
            print("train after kyc", train2.status_code, train2.json().get("detail", {}).get("code"))
            if train2.json().get("detail", {}).get("code") == "KYC_REQUIRED":
                print("KYC gate still blocking after verify", file=sys.stderr)
                return 1

    print("KYC smoke OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
