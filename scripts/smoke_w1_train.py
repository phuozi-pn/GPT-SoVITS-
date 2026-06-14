from __future__ import annotations

import sys
import time

import httpx

BASE = "http://127.0.0.1:8001"
VOICE_ID = "11111111-1111-1111-1111-111111111100"


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{BASE}/api/v1/voices/{VOICE_ID}/train",
            json={"model_tag": "gsv-v2pro-20250606"},
        )
        print("POST /voices/{id}/train", r.status_code, r.text)
        r.raise_for_status()
        body = r.json()
        assert body.get("job_type") == "train", body
        job_id = body["job_id"]

        for _ in range(30):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}")
            g.raise_for_status()
            polled = g.json()
            print("GET /jobs", polled.get("status"), polled.get("voice_version_id"))
            if polled.get("status") == "succeeded":
                assert polled.get("voice_version_id"), polled
                assert polled.get("checkpoint_uri"), polled
                print("OK", polled)
                return 0
            if polled.get("status") == "failed":
                print("FAILED", polled)
                return 1
            time.sleep(1)
    print("timeout")
    return 1


if __name__ == "__main__":
    sys.exit(main())
