"""Import cloud-trained GPT-SoVITS weights into platform VoiceVersion."""
from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

import httpx

DEFAULT_BASE = "http://127.0.0.1:8001"


def main() -> int:
    parser = argparse.ArgumentParser(description="Register engine weights for Web synthesis")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--token", default="", help="Bearer token (or DEV_SKIP_AUTH)")
    parser.add_argument("--voice-name", default="蛊真人-004")
    parser.add_argument("--label", default="cloud-004")
    parser.add_argument("--gpt", default="GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt")
    parser.add_argument("--sovits", default="SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth")
    parser.add_argument("--ref", default=r"C:\Users\panta\Desktop\ref_guzhenren.wav")
    parser.add_argument(
        "--ref-text",
        default="龙宫傲然一笑，宿命谷从来都不能被古仙运用。",
    )
    parser.add_argument("--voice-id", default="", help="Optional existing voice UUID")
    args = parser.parse_args()

    body = {
        "voice_name": args.voice_name,
        "label": args.label,
        "engine_gpt_weights": args.gpt,
        "engine_sovits_weights": args.sovits,
        "ref_audio_host_path": args.ref,
        "ref_text": args.ref_text,
        "text_split_method": "cut0",
        "temperature": 0.78,
    }
    if args.voice_id:
        body["voice_id"] = args.voice_id

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{args.base}/api/v1/voices/import-weights", json=body, headers=headers)
        print(r.status_code, r.text)
        if r.status_code >= 400:
            return 1
        data = r.json()
        print("\nImported voice_version_id:", data.get("voice_version_id"))
        print("Use in Web 音色库 or synthesis API.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
