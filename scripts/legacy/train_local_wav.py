from __future__ import annotations

"""Upload your own wav → confirm → train → optional synthesize.

Usage:
  python scripts/train_local_wav.py path/to/your.wav --ref-text "参考音频里说的内容"
  python scripts/train_local_wav.py your.wav --ref-text "..." --synth-text "合成这句试试"
"""

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
DEFAULT_SYNTH = "你好，这是我用自己的声音训练后合成的测试句子。"


def _poll_job(client: httpx.Client, job_id: str, *, label: str, max_sec: int) -> dict:
    for _ in range(max_sec // 2):
        r = client.get(f"{BASE}/api/v1/jobs/{job_id}")
        r.raise_for_status()
        body = r.json()
        status = body.get("status")
        print(f"  [{label}] {status}", end="")
        if status == "succeeded":
            print(" OK")
            return body
        if status == "failed":
            print(" FAILED")
            print(body.get("error_message", body))
            sys.exit(1)
        print()
        time.sleep(2)
    print(f"  [{label}] timeout after {max_sec}s")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload local wav and run real train job")
    parser.add_argument("wav", type=Path, help="Path to your .wav file")
    parser.add_argument("--ref-text", required=True, help="Transcript (required for short clips; QC hint for long + ASR)")
    parser.add_argument("--voice-name", default="my-voice", help="Display name for new voice")
    parser.add_argument("--synth-text", default="", help="If set, run synthesis after train")
    parser.add_argument("--train-timeout", type=int, default=900, help="Train poll seconds (default 900)")
    args = parser.parse_args()

    wav_path = args.wav.resolve()
    if not wav_path.is_file():
        print(f"File not found: {wav_path}", file=sys.stderr)
        return 2
    if wav_path.suffix.lower() != ".wav":
        print("Only .wav supported in MVP (convert flac/mp3 first)", file=sys.stderr)
        return 2

    synth_text = args.synth_text or os.environ.get("SYNTH_TEXT", "")
    data = wav_path.read_bytes()
    print(f"API: {BASE}")
    print(f"Wav: {wav_path} ({len(data)} bytes)")
    print(f"ref_text: {args.ref_text[:60]}{'...' if len(args.ref_text) > 60 else ''}")
    print()

    with httpx.Client(timeout=120.0) as client:
        v = client.post(f"{BASE}/api/v1/voices", json={"name": args.voice_name})
        v.raise_for_status()
        voice_id = v.json()["voice_id"]
        print(f"voice_id: {voice_id}")

        c = client.post(f"{BASE}/api/v1/consents", json={"voice_id": voice_id})
        c.raise_for_status()
        if c.json().get("status") != "approved":
            print("Consent not approved — check CONSENT_AUTO_APPROVE in .env")
            return 1

        u = client.post(
            f"{BASE}/api/v1/voices/assets",
            data={"voice_id": voice_id, "ref_text": args.ref_text},
            files={"audio_file": (wav_path.name, data, "audio/wav")},
        )
        print("upload QC:", u.status_code, u.text[:200])
        u.raise_for_status()
        asset = u.json()
        if not asset.get("qc_passed"):
            print("QC failed:", asset.get("qc_result"))
            print("Tip: set QC_DEV_RELAX_DURATION=true for short clips; production needs 8-15 min")
            return 1
        asset_id = asset["asset_id"]
        print(f"asset_id: {asset_id}  duration={asset['qc_result'].get('duration_sec')}s")

        cf = client.post(f"{BASE}/api/v1/voices/assets/{asset_id}/confirm")
        cf.raise_for_status()

        t = client.post(
            f"{BASE}/api/v1/voices/{voice_id}/train",
            json={"model_tag": "gsv-v2pro-20250606", "voice_asset_id": asset_id},
        )
        t.raise_for_status()
        train_job = t.json()["job_id"]
        print(f"train job: {train_job} (may take several minutes)...")

        train_result = _poll_job(client, train_job, label="train", max_sec=args.train_timeout)
        voice_version_id = train_result["voice_version_id"]
        print(f"voice_version_id: {voice_version_id}")
        print(f"checkpoint: {train_result.get('checkpoint_uri')}")

        if not synth_text:
            synth_text = DEFAULT_SYNTH
        print(f"\nsynthesis: {synth_text[:40]}...")
        s = client.post(
            f"{BASE}/api/v1/synthesis",
            json={"voice_version_id": voice_version_id, "text": synth_text},
        )
        s.raise_for_status()
        synth_job = s.json()["job_id"]
        synth_result = _poll_job(client, synth_job, label="synth", max_sec=300)
        print(f"\nDone.")
        print(f"  voice_version_id: {voice_version_id}")
        print(f"  audio_url: {synth_result.get('audio_url')}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
