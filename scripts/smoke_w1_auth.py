"""W1 smoke: login -> Bearer token -> POST /synthesis."""
from __future__ import annotations

import sys
import time

import httpx

BASE = "http://127.0.0.1:8001"
PHONE = "13800000001"
VOICE_VERSION_ID = "11111111-1111-1111-1111-111111111101"
TEXT = "你好，JWT 鉴权冒烟测试。"


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        sms = client.post(f"{BASE}/api/v1/auth/sms/send", json={"phone": PHONE})
        print("POST /auth/sms/send", sms.status_code, sms.text)
        sms.raise_for_status()
        code = sms.json().get("mock_code")
        if not code:
            print("SMS_MOCK=false; set SMS_MOCK=true or provide code manually")
            return 1

        login = client.post(f"{BASE}/api/v1/auth/login", json={"phone": PHONE, "code": code})
        print("POST /auth/login", login.status_code)
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            f"{BASE}/api/v1/synthesis",
            json={"voice_version_id": VOICE_VERSION_ID, "text": TEXT, "format": "wav"},
            headers=headers,
        )
        print("POST /synthesis", r.status_code, r.text)
        r.raise_for_status()
        job_id = r.json()["job_id"]

        for _ in range(30):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}", headers=headers)
            g.raise_for_status()
            body = g.json()
            print("GET /jobs", body.get("status"), body.get("audio_url"))
            if body.get("status") == "succeeded":
                print("OK", body)
                return 0
            if body.get("status") == "failed":
                print("FAILED", body)
                return 1
            time.sleep(1)
    print("timeout")
    return 1


if __name__ == "__main__":
    sys.exit(main())
