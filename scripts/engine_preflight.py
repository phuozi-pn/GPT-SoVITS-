"""Preflight checks for GPT-SoVITS api_v2 (port 9880) before real-engine smoke tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]

DEFAULT_GPT_WEIGHTS = "GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt"
DEFAULT_SOVITS_WEIGHTS = "SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth"


def read_dotenv_value(name: str, default: str = "") -> str:
    env_path = REPO / ".env"
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == name:
                return val.strip()
    return os.environ.get(name, default)


def engine_mock_enabled() -> bool:
    return read_dotenv_value("ENGINE_MOCK", "true").lower() in ("1", "true", "yes")


def engine_tts_url() -> str:
    return read_dotenv_value("ENGINE_TTS_URL", "http://127.0.0.1:9880").rstrip("/")


def engine_train_root() -> Path:
    raw = read_dotenv_value("ENGINE_TRAIN_ROOT", "")
    return Path(raw).resolve() if raw else Path()


def print_engine_remediation(*, engine: str, detail: str = "") -> None:
    print("\n=== 引擎未就绪（真合成需要 9880）===", file=sys.stderr)
    if detail:
        print(f"原因: {detail}", file=sys.stderr)
    print(
        f"""
当前 .env 中 ENGINE_MOCK=false，Infer Worker 会调用 {engine}。
权重文件在宿主机存在 ≠ api_v2 已加载；须先启动 Docker 容器与 api_v2。

【方案 A · 真引擎合成】
  1. 在上游目录启动 GPT-SoVITS 容器（端口 9874）：
     cd C:\\Users\\panta\\Desktop\\GPT-SOVITS\\GPT-SoVITS
     docker compose run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite
  2. 同步 .env 并启动 api_v2（start 会自动 sync）：
     cd C:\\Users\\panta\\Desktop\\GPT
     .\\scripts\\engine_sync_env.ps1
     .\\scripts\\engine_api_v2.ps1 -Action start
  3. 重启平台（让 infer worker 读到 .env）：
     .\\scripts\\platform_start.ps1
  4. 重跑：python scripts/smoke_e2e_guzhenren.py

【方案 B · 无 GPU 占位合成（仅验证平台链路）】
  1. .env 设 ENGINE_MOCK=true
  2. .\\scripts\\platform_start.ps1
  3. python scripts/smoke_e2e_guzhenren.py

手动探针（容器内权重路径须与 metadata 一致）：
  GET {engine}/set_gpt_weights?weights_path={DEFAULT_GPT_WEIGHTS}
  GET {engine}/set_sovits_weights?weights_path={DEFAULT_SOVITS_WEIGHTS}
""".strip(),
        file=sys.stderr,
    )


def check_host_weights(
    gpt_rel: str = DEFAULT_GPT_WEIGHTS,
    sovits_rel: str = DEFAULT_SOVITS_WEIGHTS,
) -> list[str]:
    root = engine_train_root()
    if not root.is_dir():
        return [f"ENGINE_TRAIN_ROOT 不存在: {root}"]
    issues: list[str] = []
    gpt = root / Path(gpt_rel.replace("\\", "/"))
    sovits = root / Path(sovits_rel.replace("\\", "/"))
    if not gpt.is_file():
        issues.append(f"宿主机缺少 GPT 权重: {gpt}")
    if not sovits.is_file():
        issues.append(f"宿主机缺少 SoVITS 权重: {sovits}")
    return issues


def preflight_engine(
    *,
    gpt_weights: str = DEFAULT_GPT_WEIGHTS,
    sovits_weights: str = DEFAULT_SOVITS_WEIGHTS,
    timeout_sec: float = 300.0,
    client: httpx.Client | None = None,
) -> None:
    """Raise SystemExit(2) when real engine is required but not ready."""
    if engine_mock_enabled():
        print("ENGINE_MOCK=true — 跳过 9880 预检（Infer Worker 使用占位 wav）")
        return

    engine = engine_tts_url()
    host_issues = check_host_weights(gpt_weights, sovits_weights)
    if host_issues:
        print_engine_remediation(engine=engine, detail="; ".join(host_issues))
        raise SystemExit(2)

    stale = read_dotenv_value("ENGINE_TRAIN_DOCKER", "")
    if stale:
        print(f"  .env ENGINE_TRAIN_DOCKER={stale} (run: .\\scripts\\engine_sync_env.ps1 if stale)")

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout_sec)

    assert client is not None
    try:
        try:
            docs = client.get(f"{engine}/docs", timeout=15.0)
        except Exception as exc:
            print_engine_remediation(engine=engine, detail=f"无法连接 {engine}/docs — {exc}")
            raise SystemExit(2) from exc

        if docs.status_code != 200:
            print_engine_remediation(
                engine=engine,
                detail=f"{engine}/docs 返回 {docs.status_code}",
            )
            raise SystemExit(2)

        for endpoint, weights in (
            ("set_gpt_weights", gpt_weights),
            ("set_sovits_weights", sovits_weights),
        ):
            resp = client.get(
                f"{engine}/{endpoint}",
                params={"weights_path": weights},
                timeout=timeout_sec,
            )
            if resp.status_code != 200:
                body = (resp.text or "").strip()[:300]
                print_engine_remediation(
                    engine=engine,
                    detail=f"{endpoint}({weights}) -> HTTP {resp.status_code} {body}",
                )
                raise SystemExit(2)
            print(f"  OK {endpoint} -> {weights}")

        print(f"Engine preflight OK: {engine}")
    finally:
        if own_client:
            client.close()


if __name__ == "__main__":
    preflight_engine()
