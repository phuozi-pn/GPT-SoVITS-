"""A/B tune: same 004 weights + ref, sweep infer params on fixed lines via api_v2 9880.

Outputs: data/tune_ab/<preset_id>/<nn>_<snippet>.wav + index.md

Env:
  ENGINE_TTS_URL     default http://127.0.0.1:9880
  GPT_WEIGHTS        default GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt
  SOVITS_WEIGHTS     default SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth
  REF_WAV            default C:\\Users\\panta\\Desktop\\ref_guzhenren.wav
  REF_TEXT           default (see below)
  PRESETS_JSON       default scripts/fixtures/tune_presets_004.json
  LINES_FILE         default scripts/fixtures/tune_lines.txt
  OUT_DIR            default data/tune_ab
"""
from __future__ import annotations

import json
import os
import re
import sys
import wave
from io import BytesIO
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
BASE = os.environ.get("ENGINE_TTS_URL", "http://127.0.0.1:9880").rstrip("/")
GPT_W = os.environ.get("GPT_WEIGHTS", "GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt")
SOVITS_W = os.environ.get("SOVITS_WEIGHTS", "SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth")
REF_WAV = Path(os.environ.get("REF_WAV", r"C:\Users\panta\Desktop\ref_guzhenren.wav"))
REF_TEXT = os.environ.get(
    "REF_TEXT",
    "龙宫傲然一笑，宿命谷从来都不能被古仙运用。",
)
PRESETS_JSON = Path(os.environ.get("PRESETS_JSON", REPO / "scripts" / "fixtures" / "tune_presets_004.json"))
LINES_FILE = Path(os.environ.get("LINES_FILE", REPO / "scripts" / "fixtures" / "tune_lines.txt"))
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO / "data" / "tune_ab"))


def _safe_name(text: str, max_len: int = 12) -> str:
    t = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return (t[:max_len] or "line")


def _ref_in_container(ref_host: Path) -> str:
    """Stage ref into engine samples; return container path."""
    engine_root = os.environ.get("ENGINE_TRAIN_ROOT", r"C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS")
    samples = Path(engine_root) / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    dst = samples / "tune_ref_guzhenren.wav"
    dst.write_bytes(ref_host.read_bytes())
    return "/workspace/GPT-SoVITS/samples/tune_ref_guzhenren.wav"


def _ensure_weights(client: httpx.Client) -> None:
    for endpoint, weights in (("set_gpt_weights", GPT_W), ("set_sovits_weights", SOVITS_W)):
        r = client.get(f"{BASE}/{endpoint}", params={"weights_path": weights}, timeout=300.0)
        if r.status_code != 200:
            raise RuntimeError(f"{endpoint} failed: {r.status_code} {r.text[:300]}")


def _synthesize(
    client: httpx.Client,
    *,
    ref_path: str,
    text: str,
    preset: dict,
) -> bytes:
    body = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref_path,
        "prompt_text": REF_TEXT,
        "prompt_lang": "zh",
        "media_type": "wav",
        "text_split_method": preset.get("text_split_method", "cut0"),
        "streaming_mode": False,
        "parallel_infer": False,
        "temperature": preset.get("temperature", 0.78),
        "speed_factor": preset.get("speed_factor", 1.0),
        "top_p": preset.get("top_p", 1.0),
    }
    r = client.post(f"{BASE}/tts", json=body, timeout=300.0)
    if r.status_code != 200:
        raise RuntimeError(f"TTS failed: {r.status_code} {r.text[:300]}")
    return r.content


def _wav_duration(data: bytes) -> float:
    with wave.open(BytesIO(data), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def main() -> int:
    if not REF_WAV.is_file():
        print(f"REF wav missing: {REF_WAV}", file=sys.stderr)
        return 2
    if not PRESETS_JSON.is_file() or not LINES_FILE.is_file():
        print("Missing presets or lines file", file=sys.stderr)
        return 2

    lines = [
        ln.strip()
        for ln in LINES_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    presets = json.loads(PRESETS_JSON.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        h = httpx.get(f"{BASE}/docs", timeout=5.0)
        h.raise_for_status()
    except Exception as exc:
        print(f"Engine not ready at {BASE}: {exc}", file=sys.stderr)
        print("Start: .\\scripts\\engine_api_v2.ps1 -Action start", file=sys.stderr)
        return 2

    ref_container = _ref_in_container(REF_WAV)
    report_rows: list[str] = ["# 004 听感 A/B 对比", "", f"ref: `{REF_WAV}`", f"ref_text: {REF_TEXT}", ""]

    with httpx.Client() as client:
        _ensure_weights(client)
        for preset in presets:
            pid = preset["id"]
            label = preset.get("label", pid)
            preset_dir = OUT_DIR / pid
            preset_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n=== {label} ({pid}) ===")
            report_rows.append(f"## {label} (`{pid}`)")
            report_rows.append("")
            report_rows.append(
                f"- cut={preset.get('text_split_method')} temp={preset.get('temperature')} "
                f"speed={preset.get('speed_factor')} top_p={preset.get('top_p')}"
            )
            report_rows.append("")

            for i, text in enumerate(lines, start=1):
                snippet = _safe_name(text)
                out_path = preset_dir / f"{i:02d}_{snippet}.wav"
                try:
                    audio = _synthesize(client, ref_path=ref_container, text=text, preset=preset)
                    out_path.write_bytes(audio)
                    dur = _wav_duration(audio)
                    print(f"  [{i}] {dur:.1f}s -> {out_path.name}")
                    report_rows.append(f"{i}. `{out_path.name}` — {text} ({dur:.1f}s)")
                except Exception as exc:
                    print(f"  [{i}] FAIL: {exc}")
                    report_rows.append(f"{i}. FAIL — {text}: {exc}")
            report_rows.append("")

    index = OUT_DIR / "index.md"
    index.write_text("\n".join(report_rows), encoding="utf-8")
    meta = {
        "ref_wav": str(REF_WAV),
        "ref_text": REF_TEXT,
        "gpt_weights": GPT_W,
        "sovits_weights": SOVITS_W,
        "presets": [p["id"] for p in presets],
        "lines": lines,
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Open folder: {OUT_DIR}")
    print(f"Index: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
