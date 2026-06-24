"""Sync platform training scripts to remote GPU when repo is outdated."""

from __future__ import annotations

import logging
import shlex
from pathlib import Path

from voice_platform.cloud_train.ssh_client import CloudTrainError, scp_to_remote, ssh_exec
from voice_platform.cloud_train.ssh_config import CloudSshConfig
from voice_platform.engine.paths import platform_root

logger = logging.getLogger(__name__)

_CLOUD_SCRIPTS = (
    "infra/engine/cloud/train.sh",
    "infra/engine/cloud/train_from_dataset.sh",
)
_ENGINE_SCRIPTS = (
    "infra/engine/scripts/spike_train_v2pro.py",
    "infra/engine/train-v2pro-spike.json",
)
_PREPARE_SCRIPT = "infra/engine/scripts/prepare_train_dataset.py"


def ensure_remote_train_scripts(
    cfg: CloudSshConfig,
    *,
    remote_platform_root: str,
    include_dataset_script: bool = False,
    include_prepare_script: bool = False,
) -> None:
    """Upload local platform scripts so remote does not need a fresh git pull."""
    local_root = platform_root()
    rels = list(_ENGINE_SCRIPTS)
    if include_prepare_script:
        rels.append(_PREPARE_SCRIPT)
    rels.extend(_CLOUD_SCRIPTS if include_dataset_script else ("infra/engine/cloud/train.sh",))

    remote_base = remote_platform_root.rstrip("/")
    for rel in rels:
        local_path = local_root / Path(rel)
        if not local_path.is_file():
            logger.warning("skip remote sync, local file missing: %s", local_path)
            continue
        remote_path = f"{remote_base}/{rel.replace(chr(92), '/')}"
        remote_dir = remote_path.rsplit("/", 1)[0]
        ssh_exec(cfg, f"mkdir -p {shlex.quote(remote_dir)}")
        scp_to_remote(cfg, local_path, remote_path)
        if remote_path.endswith(".sh"):
            ssh_exec(cfg, f"chmod +x {shlex.quote(remote_path)}")
        logger.info("cloud_train synced script -> %s", remote_path)


_REMOTE_PATH_PREFIX = "export PATH=/root/miniconda3/bin:/usr/local/bin:/usr/bin:$PATH"


def resolve_remote_python(cfg: CloudSshConfig, *, engine_root: str | None = None) -> str:
    """AutoDL / Linux images often expose python3 but not python."""
    _ = engine_root  # reserved for engine-local venv discovery
    out = ssh_exec(
        cfg,
        f"{_REMOTE_PATH_PREFIX}; "
        "for p in \"$(command -v python3 2>/dev/null)\" "
        "\"$(command -v python 2>/dev/null)\" "
        "/root/miniconda3/bin/python3 /usr/bin/python3; do "
        '[ -n "$p" ] && [ -x "$p" ] && echo "$p" && break; done',
        timeout_sec=30,
    ).strip()
    py = out.splitlines()[-1].strip() if out else ""
    if not py:
        raise CloudTrainError(
            "远端未找到 python3/python——请在 GPU 实例选择带 Python 的镜像，"
            "或 SSH 登录后确认 which python3"
        )
    return py
