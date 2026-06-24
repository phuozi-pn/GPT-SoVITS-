"""Smoke: marketplace waitlist + admin issue invite (REQ-015)."""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
CREATOR = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
ADMIN = os.environ.get("ADMIN_USER_ID", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _client(user_id: str) -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={"X-User-Id": user_id}, timeout=60.0)


def main() -> int:
    with _client(CREATOR) as creator:
        join = creator.post(
            "/api/v1/marketplace/waitlist",
            json={"contact": "smoke@test", "note": "smoke_mvp1_waitlist"},
        )
        print("join waitlist", join.status_code)
        join.raise_for_status()

        elig = creator.get("/api/v1/marketplace/publish-eligibility")
        elig.raise_for_status()
        if not elig.json().get("on_waitlist"):
            print("Expected on_waitlist=true", file=sys.stderr)
            return 1

    with _client(ADMIN) as admin:
        rows = admin.get("/api/v1/admin/marketplace/waitlist")
        rows.raise_for_status()
        pending = rows.json()
        if not pending:
            print("No pending waitlist rows", file=sys.stderr)
            return 1
        target = next(
            (r for r in pending if r.get("user_id") == CREATOR),
            pending[0],
        )
        wid = target["waitlist_id"]
        issue = admin.post(f"/api/v1/admin/marketplace/waitlist/{wid}/issue-invite", json={})
        print("issue invite", issue.status_code, issue.json().get("code"))
        issue.raise_for_status()

    with _client(CREATOR) as creator:
        elig = creator.get("/api/v1/marketplace/publish-eligibility")
        elig.raise_for_status()
        body = elig.json()
        if not body.get("invited"):
            print("Expected invited=true after issue", file=sys.stderr)
            return 1

    print("Waitlist + admin issue-invite smoke OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
