"""Smoke: create API key → open synthesis → poll job."""

from __future__ import annotations

import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
USER = os.environ.get("GRANT_OWNER_ID", "00000000-0000-0000-0000-000000000001")
VOICE = os.environ.get("SMOKE_VOICE_VERSION_ID", "")


def _client(user_id: str | None = None) -> httpx.Client:
    headers: dict[str, str] = {}
    if user_id:
        headers["X-User-Id"] = user_id
    return httpx.Client(base_url=BASE, headers=headers, timeout=60.0)


def _pick_version(client: httpx.Client) -> str:
    if VOICE:
        return VOICE
    versions = client.get("/api/v1/voice-versions")
    versions.raise_for_status()
    owned = [v for v in versions.json() if not v.get("granted")]
    if not owned:
        raise RuntimeError("No voice versions for open API smoke")
    return owned[0]["voice_version_id"]


def main() -> int:
    with _client(USER) as owner:
        version_id = _pick_version(owner)
        print("voice_version_id", version_id)

        created = owner.post("/api/v1/developer/api-keys", json={"name": "smoke-open-api"})
        print("create key", created.status_code)
        created.raise_for_status()
        api_key = created.json()["api_key"]
        print("key_prefix", created.json()["key_prefix"])

    with httpx.Client(base_url=BASE, timeout=120.0) as open_client:
        synth = open_client.post(
            "/api/v1/open/synthesis",
            headers={"X-Api-Key": api_key},
            json={"voice_version_id": version_id, "text": "Open API smoke test."},
        )
        print("open synthesis", synth.status_code)
        synth.raise_for_status()
        job_id = synth.json()["job_id"]
        print("job_id", job_id)

        deadline = time.time() + 120
        while time.time() < deadline:
            job = open_client.get(f"/api/v1/open/jobs/{job_id}", headers={"X-Api-Key": api_key})
            job.raise_for_status()
            status = job.json()["status"]
            print("job status", status)
            if status in ("succeeded", "failed"):
                if status != "succeeded":
                    print("Job failed:", job.json().get("error_message"), file=sys.stderr)
                    return 1
                if not job.json().get("audio_url"):
                    print("Missing audio_url", file=sys.stderr)
                    return 1
                print("Open API smoke OK", job.json()["audio_url"])
                return 0
            time.sleep(2)

    print("Job poll timeout", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print("HTTP error:", exc, file=sys.stderr)
        sys.exit(1)
