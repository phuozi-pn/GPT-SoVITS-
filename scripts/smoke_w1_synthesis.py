"""W1 smoke: POST /synthesis -> poll GET /jobs/{id} until succeeded."""
from __future__ import annotations

import sys
import time

import httpx

BASE = "http://127.0.0.1:8001"
VOICE_VERSION_ID = "11111111-1111-1111-1111-111111111101"
TEXT = "你好，这是一次 W1 API 合成测试。"


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{BASE}/api/v1/synthesis",
            json={"voice_version_id": VOICE_VERSION_ID, "text": TEXT, "format": "wav"},
        )
        print("POST /synthesis", r.status_code, r.text)
        r.raise_for_status()
        job_id = r.json()["job_id"]

        for _ in range(30):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}")
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
