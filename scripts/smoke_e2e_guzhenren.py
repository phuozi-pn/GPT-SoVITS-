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

CLI:
  --skip-single         跳过单条合成（仅跑批量）
  --csv PATH            指定 CSV
  --expect-failed-min N 期望至少 N 行失败（mixed 敏感词用例）
  --expect-succeeded-min N 期望至少 N 行成功（默认 1）
  --skip-preflight      跳过 9880 预检
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO / "scripts" / "fixtures" / "guzhenren_batch_20.csv"


def _load_preflight():
    import importlib.util

    path = REPO / "scripts" / "engine_preflight.py"
    spec = importlib.util.spec_from_file_location("engine_preflight", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.preflight_engine


preflight_engine = _load_preflight()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MVP-0 end-to-end smoke (synth + batch + export)")
    p.add_argument("--skip-single", action="store_true", help="Skip single synthesis step")
    p.add_argument("--csv", type=Path, default=None, help="Batch CSV path")
    p.add_argument("--expect-failed-min", type=int, default=0, help="Require at least N failed lines")
    p.add_argument("--expect-succeeded-min", type=int, default=1, help="Require at least N succeeded lines")
    p.add_argument("--skip-preflight", action="store_true", help="Skip engine 9880 preflight")
    return p.parse_args()


def _poll_job(client: httpx.Client, job_id: str, *, base: str, timeout_sec: int) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        r = client.get(f"{base}/api/v1/jobs/{job_id}")
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        extra = ""
        if data.get("succeeded_count") is not None:
            extra = f" ok={data['succeeded_count']}"
        if data.get("failed_count"):
            extra += f" fail={data['failed_count']}"
        print(f"  job {job_id[:8]}… status={status}{extra}")
        if status in ("succeeded", "failed"):
            return data
        time.sleep(2)
    raise TimeoutError(f"job {job_id} timed out after {timeout_sec}s")


def _pick_voice_version(client: httpx.Client, *, base: str, skip_import: bool) -> str:
    r = client.get(f"{base}/api/v1/voice-versions")
    r.raise_for_status()
    versions = r.json()
    if versions:
        preferred = next((v for v in versions if "004" in (v.get("label") or "")), versions[0])
        vid = preferred["voice_version_id"]
        print(f"Using voice: {preferred.get('voice_name')} v{preferred.get('version')} {vid}")
        return vid

    if skip_import:
        print("No voice versions and SKIP_IMPORT=1", file=sys.stderr)
        sys.exit(2)

    print("No voice versions — importing cloud-004 defaults…")
    imp = client.post(
        f"{base}/api/v1/voices/import-weights",
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
    args = _parse_args()
    base = os.environ.get("API_BASE", "http://127.0.0.1:8001")
    csv_path = args.csv or Path(os.environ.get("CSV_PATH", DEFAULT_CSV))
    role_name = os.environ.get("ROLE_NAME", "龙宫")
    project_name = os.environ.get("PROJECT_NAME", "蛊真人试单")
    synth_line = os.environ.get("SYNTH_LINE", "方源，你给我出来！")
    out_dir = Path(os.environ.get("OUT_DIR", REPO / "data" / "e2e_out"))
    poll_timeout = int(os.environ.get("POLL_TIMEOUT_SEC", "900"))
    skip_import = os.environ.get("SKIP_IMPORT", "").lower() in ("1", "true", "yes")

    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {"csv": str(csv_path), "steps": []}

    with httpx.Client(timeout=120.0) as client:
        h = client.get(f"{base}/health")
        print("health", h.status_code, h.text)
        h.raise_for_status()

        voice_version_id = _pick_voice_version(client, base=base, skip_import=skip_import)
        summary["voice_version_id"] = voice_version_id

        if not args.skip_preflight:
            print("\n=== Engine preflight ===")
            preflight_engine()

        if not args.skip_single:
            print("\n=== Step 1: single synthesis ===")
            s = client.post(
                f"{base}/api/v1/synthesis",
                json={
                    "voice_version_id": voice_version_id,
                    "text": synth_line,
                    "format": "wav",
                    "ai_disclosure_ack": True,
                },
            )
            print("POST /synthesis", s.status_code)
            s.raise_for_status()
            syn_job = s.json()["job_id"]
            syn_result = _poll_job(client, syn_job, base=base, timeout_sec=poll_timeout)
            summary["steps"].append({"single_synth": syn_result.get("status")})
            if syn_result.get("status") != "succeeded":
                print("Single synth failed:", syn_result)
                err = syn_result.get("error_message") or ""
                if "set_gpt_weights" in err or "Engine TTS failed" in err:
                    print(
                        "\n提示: 真引擎合成失败。先运行 .\\scripts\\engine_api_v2.ps1 -Action start，"
                        "或 .env 设 ENGINE_MOCK=true 后 platform_start.ps1 重启。",
                        file=sys.stderr,
                    )
                return 1

            export_r = client.get(f"{base}/api/v1/exports/{syn_job}/download")
            if export_r.status_code == 200:
                out_wav = out_dir / f"single_{syn_job[:8]}.wav"
                out_wav.write_bytes(export_r.content)
                print(f"Saved compliant single wav: {out_wav}")
                summary["single_export"] = str(out_wav)

        print("\n=== Step 2: project batch ===")
        p = client.post(f"{base}/api/v1/projects", json={"name": project_name})
        print("POST /projects", p.status_code)
        p.raise_for_status()
        project_id = p.json()["project_id"]
        summary["project_id"] = project_id

        br = client.post(
            f"{base}/api/v1/projects/{project_id}/roles",
            json={"role_name": role_name, "voice_version_id": voice_version_id},
        )
        print("POST /roles", br.status_code)
        br.raise_for_status()

        csv_bytes = csv_path.read_bytes()
        batch = client.post(
            f"{base}/api/v1/projects/{project_id}/batch",
            files={"file": (csv_path.name, csv_bytes, "text/csv")},
        )
        print("POST /batch", batch.status_code, batch.text[:200])
        batch.raise_for_status()
        batch_job = batch.json()["job_id"]
        line_count = batch.json().get("line_count")
        print(f"Batch job {batch_job}, lines={line_count}")

        batch_result = _poll_job(client, batch_job, base=base, timeout_sec=poll_timeout)
        succeeded = batch_result.get("succeeded_count") or 0
        failed = batch_result.get("failed_count") or 0
        summary["batch"] = {
            "status": batch_result.get("status"),
            "succeeded_count": succeeded,
            "failed_count": failed,
        }

        if batch_result.get("status") != "succeeded":
            print("Batch failed:", batch_result.get("error_message"))
            return 1

        if succeeded < args.expect_succeeded_min:
            print(
                f"Expected at least {args.expect_succeeded_min} succeeded lines, got {succeeded}",
                file=sys.stderr,
            )
            return 1
        if failed < args.expect_failed_min:
            print(
                f"Expected at least {args.expect_failed_min} failed lines, got {failed}",
                file=sys.stderr,
            )
            return 1

        zip_r = client.get(f"{base}/api/v1/exports/{batch_job}/download")
        if zip_r.status_code == 200:
            zip_path = out_dir / f"batch_{batch_job[:8]}.zip"
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
                    failures = manifest.get("failures", [])
                    summary["manifest_failures"] = failures
                    if failures:
                        print(f"Manifest failures ({len(failures)}):")
                        for f in failures:
                            print(f"  - line {f.get('index')}: {f.get('error') or f.get('message')}")

    report_name = "e2e_report_mixed.json" if args.expect_failed_min else "e2e_report.json"
    report = out_dir / report_name
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== OK === report: {report}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
