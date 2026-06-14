"""End-to-end trial: import/list voice → single synth → project CSV batch → compliant export.

Env:
  API_BASE              default http://127.0.0.1:8001
  CSV_PATH              default scripts/fixtures/guzhenren_batch_20.csv
  ROLE_NAME             default 龙宫
  PROJECT_NAME          default 蛊真人试单
  SYNTH_LINE            default 方源，你给我出来！
  SKIP_IMPORT           1 = do not auto-import weights
  OUT_DIR               default ./data/e2e_out (gitignored via data/)
  POLL_TIMEOUT_SEC      default 900
"""
from __future__ import annotations

import json
import os
import sys
import time
import zipfile
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")
CSV_PATH = Path(os.environ.get("CSV_PATH", REPO / "scripts" / "fixtures" / "guzhenren_batch_20.csv"))
ROLE_NAME = os.environ.get("ROLE_NAME", "龙宫")
PROJECT_NAME = os.environ.get("PROJECT_NAME", "蛊真人试单")
SYNTH_LINE = os.environ.get("SYNTH_LINE", "方源，你给我出来！")
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO / "data" / "e2e_out"))
POLL_TIMEOUT_SEC = int(os.environ.get("POLL_TIMEOUT_SEC", "900"))
SKIP_IMPORT = os.environ.get("SKIP_IMPORT", "").lower() in ("1", "true", "yes")


def _poll_job(client: httpx.Client, job_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT_SEC
    while time.time() < deadline:
        r = client.get(f"{BASE}/api/v1/jobs/{job_id}")
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        print(f"  job {job_id[:8]}… status={status}")
        if status in ("succeeded", "failed"):
            return data
        time.sleep(2)
    raise TimeoutError(f"job {job_id} timed out after {POLL_TIMEOUT_SEC}s")


def _pick_voice_version(client: httpx.Client) -> str:
    r = client.get(f"{BASE}/api/v1/voice-versions")
    r.raise_for_status()
    versions = r.json()
    if versions:
        preferred = next((v for v in versions if "004" in (v.get("label") or "")), versions[0])
        vid = preferred["voice_version_id"]
        print(f"Using voice: {preferred.get('voice_name')} v{preferred.get('version')} {vid}")
        return vid

    if SKIP_IMPORT:
        print("No voice versions and SKIP_IMPORT=1", file=sys.stderr)
        sys.exit(2)

    print("No voice versions — importing cloud-004 defaults…")
    imp = client.post(
        f"{BASE}/api/v1/voices/import-weights",
        json={
            "voice_name": "蛊真人-004",
            "label": "cloud-004",
            "engine_gpt_weights": "GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt",
            "engine_sovits_weights": "SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth",
            "ref_audio_host_path": r"C:\Users\panta\Desktop\ref_guzhenren.wav",
            "ref_text": "龙宫傲然一笑，宿命谷从来都不能被古仙运用。",
            "text_split_method": "cut0",
            "temperature": 0.78,
            "speed_factor": 1.05,
            "top_p": 1.0,
        },
    )
    print("POST import-weights", imp.status_code, imp.text[:300])
    imp.raise_for_status()
    vid = imp.json()["voice_version_id"]
    print("Imported voice_version_id:", vid)
    return vid


def main() -> int:
    if not CSV_PATH.is_file():
        print(f"CSV not found: {CSV_PATH}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict = {"steps": []}

    with httpx.Client(timeout=120.0) as client:
        h = client.get(f"{BASE}/health")
        print("health", h.status_code, h.text)
        h.raise_for_status()

        voice_version_id = _pick_voice_version(client)
        summary["voice_version_id"] = voice_version_id

        # 1) Single synthesis
        print("\n=== Step 1: single synthesis ===")
        s = client.post(
            f"{BASE}/api/v1/synthesis",
            json={
                "voice_version_id": voice_version_id,
                "text": SYNTH_LINE,
                "format": "wav",
                "ai_disclosure_ack": True,
            },
        )
        print("POST /synthesis", s.status_code)
        s.raise_for_status()
        syn_job = s.json()["job_id"]
        syn_result = _poll_job(client, syn_job)
        summary["steps"].append({"single_synth": syn_result.get("status")})
        if syn_result.get("status") != "succeeded":
            print("Single synth failed:", syn_result)
            return 1

        export_r = client.get(f"{BASE}/api/v1/exports/{syn_job}/download")
        if export_r.status_code == 200:
            out_wav = OUT_DIR / f"single_{syn_job[:8]}.wav"
            out_wav.write_bytes(export_r.content)
            print(f"Saved compliant single wav: {out_wav}")
            summary["single_export"] = str(out_wav)

        # 2) Project + batch
        print("\n=== Step 2: project batch ===")
        p = client.post(f"{BASE}/api/v1/projects", json={"name": PROJECT_NAME})
        print("POST /projects", p.status_code)
        p.raise_for_status()
        project_id = p.json()["project_id"]
        summary["project_id"] = project_id

        br = client.post(
            f"{BASE}/api/v1/projects/{project_id}/roles",
            json={"role_name": ROLE_NAME, "voice_version_id": voice_version_id},
        )
        print("POST /roles", br.status_code)
        br.raise_for_status()

        csv_bytes = CSV_PATH.read_bytes()
        batch = client.post(
            f"{BASE}/api/v1/projects/{project_id}/batch",
            files={"file": (CSV_PATH.name, csv_bytes, "text/csv")},
        )
        print("POST /batch", batch.status_code, batch.text[:200])
        batch.raise_for_status()
        batch_job = batch.json()["job_id"]
        line_count = batch.json().get("line_count")
        print(f"Batch job {batch_job}, lines={line_count}")

        batch_result = _poll_job(client, batch_job)
        summary["batch"] = {
            "status": batch_result.get("status"),
            "succeeded_count": batch_result.get("succeeded_count"),
            "failed_count": batch_result.get("failed_count"),
        }

        if batch_result.get("status") != "succeeded":
            print("Batch failed:", batch_result.get("error_message"))
            return 1

        zip_r = client.get(f"{BASE}/api/v1/exports/{batch_job}/download")
        if zip_r.status_code == 200:
            zip_path = OUT_DIR / f"batch_{batch_job[:8]}.zip"
            zip_path.write_bytes(zip_r.content)
            print(f"Saved compliant ZIP: {zip_path}")
            summary["batch_export"] = str(zip_path)

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                print(f"ZIP entries ({len(names)}):")
                for name in names[:15]:
                    print(f"  - {name}")
                if len(names) > 15:
                    print(f"  … +{len(names) - 15} more")
                summary["zip_files"] = names
                if "manifest.json" in names:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                    summary["manifest_failures"] = manifest.get("failures", [])

    report = OUT_DIR / "e2e_report.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== OK === report: {report}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
