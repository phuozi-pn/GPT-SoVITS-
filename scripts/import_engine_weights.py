"""Import cloud-trained GPT-SoVITS weights into platform VoiceVersion."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

DEFAULT_BASE = "http://127.0.0.1:8001"


def _load_from_result_json(path: Path) -> tuple[str, str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    gpt = str(data.get("gpt_checkpoint") or "").strip()
    sovits = str(data.get("sovits_checkpoint") or "").strip()
    label = str(data.get("exp_name") or "").strip()
    if not gpt or not sovits:
        raise SystemExit(f"result.json missing checkpoints: {path}")
    return gpt, sovits, label


def main() -> int:
    parser = argparse.ArgumentParser(description="Register engine weights for Web synthesis")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--token", default="", help="Bearer token (or DEV_SKIP_AUTH)")
    parser.add_argument("--voice-name", default="导入音色")
    parser.add_argument("--label", default="")
    parser.add_argument("--gpt", default="", help="Relative path under ENGINE_TRAIN_ROOT")
    parser.add_argument("--sovits", default="", help="Relative path under ENGINE_TRAIN_ROOT")
    parser.add_argument("--ref", default="", help="Host absolute path to ref wav")
    parser.add_argument("--ref-text", required=True)
    parser.add_argument("--voice-id", default="", help="Optional existing voice UUID")
    parser.add_argument(
        "--from-result-json",
        default="",
        help="Cloud train result.json — auto-fill --gpt/--sovits/--label",
    )
    args = parser.parse_args()

    gpt = args.gpt
    sovits = args.sovits
    label = args.label
    if args.from_result_json:
        gpt, sovits, exp = _load_from_result_json(Path(args.from_result_json))
        if not label:
            label = exp

    if not gpt or not sovits or not args.ref:
        parser.error("Provide --gpt/--sovits/--ref or use --from-result-json with --ref")

    body = {
        "voice_name": args.voice_name,
        "label": label,
        "engine_gpt_weights": gpt,
        "engine_sovits_weights": sovits,
        "ref_audio_host_path": args.ref,
        "ref_text": args.ref_text,
        "text_split_method": "cut0",
        "temperature": 0.78,
        "speed_factor": 1.05,
        "top_p": 1.0,
    }
    if args.voice_id:
        body["voice_id"] = args.voice_id

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    with httpx.Client(timeout=120.0) as client:
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
