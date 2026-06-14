from __future__ import annotations

"""Synthesize with real 9880 using a trained voice_version_id."""

import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
VOICE_VERSION = os.environ.get("VOICE_VERSION_ID", "")
TEXT = os.environ.get("SYNTH_TEXT", "你好，这是用我上传的音频训练后合成的测试。")


def main() -> int:
    if not VOICE_VERSION:
        print("Set VOICE_VERSION_ID=<uuid from train job>", file=sys.stderr)
        return 2

    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{BASE}/api/v1/synthesis",
            json={"voice_version_id": VOICE_VERSION, "text": TEXT},
        )
        print("POST /synthesis", r.status_code, r.text)
        r.raise_for_status()
        job_id = r.json()["job_id"]

        for _ in range(90):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}")
            g.raise_for_status()
            polled = g.json()
            print("GET /jobs", polled.get("status"), polled.get("audio_url"))
            if polled.get("status") == "succeeded":
                print("OK", polled)
                return 0
            if polled.get("status") == "failed":
                print("FAILED", polled)
                return 1
            time.sleep(2)
    print("timeout")
    return 1


if __name__ == "__main__":
    sys.exit(main())
