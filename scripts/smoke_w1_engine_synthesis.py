"""W1 smoke with real engine (9880). Skip gracefully if engine down."""
from __future__ import annotations

import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
ENGINE = os.environ.get("ENGINE_TTS_URL", "http://127.0.0.1:9880")
VOICE = "11111111-1111-1111-1111-111111111101"
TEXT = "你好，这是 W1 真引擎链路测试。"


def main() -> int:
    with httpx.Client(timeout=5.0) as c:
        try:
            c.get(f"{ENGINE}/docs")
        except Exception as exc:
            print(f"SKIP: engine not reachable at {ENGINE}: {exc}")
            return 0

    print("Engine up, submitting synthesis job (ENGINE_MOCK must be false on worker)...")
    with httpx.Client(timeout=300.0) as client:
        r = client.post(
            f"{BASE}/api/v1/synthesis",
            json={"voice_version_id": VOICE, "text": TEXT, "format": "wav"},
        )
        print("POST", r.status_code, r.text[:200])
        r.raise_for_status()
        job_id = r.json()["job_id"]

        for i in range(120):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}")
            g.raise_for_status()
            body = g.json()
            print(f"poll {i}", body.get("status"), body.get("audio_url"))
            if body.get("status") == "succeeded":
                size = client.head(body["audio_url"]).headers.get("content-length", "?")
                print("OK", body, f"content-length={size}")
                return 0
            if body.get("status") == "failed":
                print("FAILED", body)
                return 1
            time.sleep(2)
    print("timeout")
    return 1


if __name__ == "__main__":
    sys.exit(main())
