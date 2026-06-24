from __future__ import annotations

"""End-to-end: create voice → consent → upload wav → confirm → train (needs API + workers)."""

import io
import os
import sys
import time
import wave
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
REF_TEXT = "大家好，我是测试用户，今天我们来测试一下语音合成功能。"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = REPO_ROOT / "infra" / "engine" / "samples" / "ref_zh_zero_shot.wav"
POLL_SEC = int(os.environ.get("SMOKE_TRAIN_POLL_SEC", "600"))


def _make_silent_wav_bytes(duration_sec: float = 5.0, sample_rate: int = 32000) -> bytes:
    """Silent wav — OK for mock train / QC only; real engine preprocess will fail."""
    buf = io.BytesIO()
    nframes = int(duration_sec * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * nframes)
    return buf.getvalue()


def _load_wav_bytes() -> tuple[bytes, str]:
    if os.environ.get("SMOKE_USE_SILENT_WAV", "").lower() in ("1", "true", "yes"):
        print("WARN: using silent wav (TRAIN_MOCK=true only)")
        return _make_silent_wav_bytes(5.0), "smoke-silent.wav"
    sample = Path(os.environ.get("SMOKE_SAMPLE_WAV", str(DEFAULT_SAMPLE)))
    if sample.is_file():
        print(f"Using sample wav: {sample}")
        return sample.read_bytes(), sample.name
    print(f"WARN: {sample} missing, falling back to silent wav")
    return _make_silent_wav_bytes(5.0), "smoke-silent.wav"


def _ensure_kyc(client: httpx.Client) -> None:
    status = client.get(f"{BASE}/api/v1/kyc/status")
    if status.status_code != 200:
        return
    body = status.json()
    if not body.get("required") or body.get("verified"):
        return
    submit = client.post(
        f"{BASE}/api/v1/kyc/submit",
        json={"real_name": "测试用户", "id_number": "110101199001011234"},
    )
    print("POST /kyc/submit", submit.status_code, submit.text)
    submit.raise_for_status()


def main() -> int:
    wav, wav_name = _load_wav_bytes()
    with httpx.Client(timeout=120.0) as client:
        _ensure_kyc(client)
        v = client.post(f"{BASE}/api/v1/voices", json={"name": "smoke-upload-voice"})
        print("POST /voices", v.status_code, v.text)
        v.raise_for_status()
        voice_id = v.json()["voice_id"]

        c = client.post(f"{BASE}/api/v1/consents", json={"voice_id": voice_id})
        print("POST /consents", c.status_code, c.text)
        c.raise_for_status()
        assert c.json()["status"] == "approved", c.json()

        u = client.post(
            f"{BASE}/api/v1/voices/assets",
            data={"voice_id": voice_id, "ref_text": REF_TEXT},
            files={"audio_file": (wav_name, wav, "audio/wav")},
        )
        print("POST /voices/assets", u.status_code, u.text)
        u.raise_for_status()
        asset_id = u.json()["asset_id"]
        if not u.json().get("qc_passed"):
            print("QC failed (set QC_DEV_RELAX_DURATION=true for short sample):", u.json())
            return 1

        cf = client.post(f"{BASE}/api/v1/voices/assets/{asset_id}/confirm")
        print("POST confirm", cf.status_code, cf.text)
        cf.raise_for_status()

        t = client.post(
            f"{BASE}/api/v1/voices/{voice_id}/train",
            json={"model_tag": "gsv-v2pro-20250606", "voice_asset_id": asset_id},
        )
        print("POST /train", t.status_code, t.text)
        t.raise_for_status()
        job_id = t.json()["job_id"]

        for _ in range(POLL_SEC // 2):
            g = client.get(f"{BASE}/api/v1/jobs/{job_id}")
            g.raise_for_status()
            polled = g.json()
            print("GET /jobs", polled.get("status"), polled.get("voice_version_id"))
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
