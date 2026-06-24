"""Sync and validate remote GPU environment before cloud training."""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass

from voice_platform.cloud_train.remote_scripts import (
    _REMOTE_PATH_PREFIX,
    ensure_remote_train_scripts,
    resolve_remote_python,
)
from voice_platform.cloud_train.ssh_client import CloudTrainError, ssh_exec
from voice_platform.cloud_train.ssh_config import CloudSshConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RemoteTrainEnvironment:
    python: str
    engine_root: str
    platform_root: str
    remote_work_dir: str
    torch_version: str
    gpu_available: bool
    checks: tuple[dict, ...]


def ensure_remote_train_environment(
    cfg: CloudSshConfig,
    *,
    local_dataset_prep: bool = True,
    sync_scripts: bool = True,
) -> RemoteTrainEnvironment:
    """Sync platform scripts and verify remote GPT-SoVITS runtime before training."""
    checks: list[dict] = []

    out = ssh_exec(cfg, "echo ok", timeout_sec=30)
    if "ok" not in out:
        raise CloudTrainError(f"SSH 握手异常: {out.strip()[:200]}")
    checks.append({"name": "ssh", "ok": True, "detail": "connected"})

    engine_root = (cfg.remote_engine_root or "/root/autodl-tmp/GPT-SoVITS").strip()
    platform_root = (cfg.remote_platform_root or "/root/autodl-tmp/GPT").strip()
    remote_work = (cfg.remote_work_dir or "/root/autodl-tmp/cloud_train_jobs").strip()

    if sync_scripts:
        ensure_remote_train_scripts(
            cfg,
            remote_platform_root=platform_root,
            include_dataset_script=local_dataset_prep,
            include_prepare_script=not local_dataset_prep,
        )
        mode = "dataset" if local_dataset_prep else "full"
        checks.append({"name": "scripts", "ok": True, "detail": f"synced ({mode})"})

    ssh_exec(cfg, f"test -f {shlex.quote(engine_root)}/webui.py", timeout_sec=30)
    checks.append({"name": "engine_root", "ok": True, "detail": engine_root})

    train_script = (
        f"{platform_root.rstrip('/')}/infra/engine/cloud/train_from_dataset.sh"
        if local_dataset_prep
        else f"{platform_root.rstrip('/')}/infra/engine/cloud/train.sh"
    )
    ssh_exec(cfg, f"test -f {shlex.quote(train_script)}", timeout_sec=30)
    checks.append({"name": "platform_root", "ok": True, "detail": platform_root})

    python = resolve_remote_python(cfg, engine_root=engine_root)
    checks.append({"name": "python3", "ok": True, "detail": python})

    torch_out = ssh_exec(
        cfg,
        f"{_REMOTE_PATH_PREFIX}; {shlex.quote(python)} -c "
        '"import torch; print(torch.__version__)"',
        timeout_sec=60,
    ).strip()
    torch_version = torch_out.splitlines()[-1].strip() if torch_out else ""
    if not torch_version:
        raise CloudTrainError("远端 Python 无法 import torch——请使用带 PyTorch 的 GPT-SoVITS 镜像")
    checks.append({"name": "torch", "ok": True, "detail": torch_version})

    gpu_out = ssh_exec(
        cfg,
        f"{_REMOTE_PATH_PREFIX}; {shlex.quote(python)} -c "
        '"import torch; print(1 if torch.cuda.is_available() else 0)"',
        timeout_sec=60,
    ).strip()
    gpu_available = gpu_out.splitlines()[-1].strip() == "1"
    if not gpu_available:
        raise CloudTrainError(
            "远端未检测到可用 GPU（torch.cuda.is_available()=False）——请确认实例已开机且为 GPU 机型"
        )
    checks.append({"name": "gpu", "ok": True, "detail": "cuda available"})

    ssh_exec(cfg, f"mkdir -p {shlex.quote(remote_work)}", timeout_sec=30)
    checks.append({"name": "work_dir", "ok": True, "detail": remote_work})

    logger.info(
        "cloud_train remote env ready python=%s torch=%s engine=%s",
        python,
        torch_version,
        engine_root,
    )
    return RemoteTrainEnvironment(
        python=python,
        engine_root=engine_root,
        platform_root=platform_root,
        remote_work_dir=remote_work,
        torch_version=torch_version,
        gpu_available=gpu_available,
        checks=tuple(checks),
    )
