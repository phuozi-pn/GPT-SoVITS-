"""Smoke: user directory, messaging, voice demo download."""
from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def headers(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        r = client.get("/health")
        if r.status_code != 200:
            print("API down:", r.status_code, file=sys.stderr)
            return 1

        patch = client.patch(
            "/api/v1/users/me/profile",
            headers=headers(USER_A),
            json={"display_name": "测试创作者A", "bio": "欢迎来访我的主页"},
        )
        print("profile patch", patch.status_code)
        if patch.status_code == 404 or patch.status_code == 405:
            print("WARN: social routes not loaded. Restart API: .\\scripts\\platform_stop.ps1 then .\\scripts\\platform_start.ps1", file=sys.stderr)
            return 2

        directory = client.get("/api/v1/users/directory", headers=headers(USER_B))
        print("directory", directory.status_code, len(directory.json()) if directory.status_code == 200 else "-")
        if directory.status_code != 200:
            print("WARN: user directory failed", directory.text[:200], file=sys.stderr)
            return 2

        msg = client.post(
            "/api/v1/messages",
            headers=headers(USER_B),
            json={"recipient_user_id": USER_A, "body": "你好，想咨询音色授权"},
        )
        print("send message", msg.status_code)
        if msg.status_code != 201:
            print("WARN: send message failed", msg.text[:200], file=sys.stderr)
            return 2

        thread = client.get(f"/api/v1/messages/with/{USER_A}", headers=headers(USER_B))
        print("thread", thread.status_code, len(thread.json()) if thread.status_code == 200 else "-")
        if thread.status_code != 200:
            print("WARN: list thread failed", thread.text[:200], file=sys.stderr)
            return 2

        catalog = client.get("/api/v1/catalog/voices", headers=headers(USER_B))
        entries = catalog.json()
        if entries:
            picked = next((e for e in entries if e.get("demo_audio_url")), entries[0])
            cid = picked["catalog_id"]
            if not picked.get("demo_audio_url"):
                print("WARN: no demo_audio_url in catalog; skip download smoke", file=sys.stderr)
            else:
                demo = client.get(f"/api/v1/catalog/voices/{cid}/demo-download", headers=headers(USER_B))
                print("demo download", demo.status_code, demo.headers.get("content-type"))
                pack = client.get(f"/api/v1/catalog/voices/{cid}/voice-pack", headers=headers(USER_B))
                print("voice pack", pack.status_code, pack.headers.get("content-type"))
                if demo.status_code != 200 or pack.status_code != 200:
                    print(
                        "WARN: download endpoints failed; ensure demo exists and user has access",
                        file=sys.stderr,
                    )
                    return 2
        else:
            print("no catalog entries for download smoke")

    print("smoke_mvp1_social OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
