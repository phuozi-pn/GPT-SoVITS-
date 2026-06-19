"""Smoke test: VoiceGrant cross-user access (DEV_SKIP_AUTH + X-User-Id)."""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
OWNER = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
GRANTEE = os.environ.get("GRANTEE_ID", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _client(user_id: str) -> httpx.Client:
    return httpx.Client(
        base_url=BASE,
        headers={"X-User-Id": user_id},
        timeout=30.0,
    )


def main() -> int:
    with _client(OWNER) as owner:
        voices = owner.get("/api/v1/voices")
        print("GET /voices (owner)", voices.status_code)
        voices.raise_for_status()
        items = voices.json()
        if not items:
            print("No voices for owner — import 004 in library first.", file=sys.stderr)
            return 2
        voice_id = items[0]["voice_id"]
        print("voice_id", voice_id)

        grant = owner.post(
            f"/api/v1/voices/{voice_id}/grants",
            json={"grantee_user_id": GRANTEE},
        )
        print("POST /grants", grant.status_code, grant.text)
        grant.raise_for_status()

        issued = owner.get("/api/v1/voice-grants/issued")
        print("GET /voice-grants/issued", issued.status_code, len(issued.json()))

    with _client(GRANTEE) as grantee:
        received = grantee.get("/api/v1/voice-grants")
        print("GET /voice-grants (grantee)", received.status_code, received.json())
        received.raise_for_status()
        if not received.json():
            print("Grantee has no grants", file=sys.stderr)
            return 1

        versions = grantee.get("/api/v1/voice-versions")
        print("GET /voice-versions (grantee)", versions.status_code, len(versions.json()))
        versions.raise_for_status()
        granted = [v for v in versions.json() if v.get("granted")]
        if not granted:
            print("Granted versions not visible to grantee", file=sys.stderr)
            return 1
        print("OK granted version", granted[0]["voice_name"], granted[0].get("label"))

    print("VoiceGrant smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
