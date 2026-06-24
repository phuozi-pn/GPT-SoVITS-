from __future__ import annotations

import logging
import shlex
import subprocess
import tarfile
import tempfile
from pathlib import Path

from voice_platform.cloud_train.ssh_config import CloudSshConfig

logger = logging.getLogger(__name__)


class CloudTrainError(RuntimeError):
    """SSH / SCP failure during cloud training."""


def _ssh_target(config: CloudSshConfig) -> str:
    return f"{config.user}@{config.host}"


def _openssh_common_args(config: CloudSshConfig, *, key_path: Path | None) -> list[str]:
    args = [
        "-p",
        str(config.port or 22),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if key_path:
        args.extend(["-i", str(key_path)])
    return args


def ssh_exec(config: CloudSshConfig, remote_cmd: str, *, timeout_sec: int | None = None) -> str:
    if config.uses_password:
        from voice_platform.cloud_train.paramiko_transport import ssh_exec_password

        return ssh_exec_password(config, remote_cmd, timeout_sec=timeout_sec)

    key_path: Path | None = None
    tmp_key = None
    if config.private_key_pem:
        tmp_key = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8")
        tmp_key.write(config.private_key_pem)
        tmp_key.flush()
        tmp_key.close()
        key_path = Path(tmp_key.name)
        try:
            key_path.chmod(0o600)
        except OSError:
            pass

    cmd = ["ssh", *_openssh_common_args(config, key_path=key_path), _ssh_target(config), remote_cmd]
    logger.info("cloud_train ssh: %s", remote_cmd[:200])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "ssh failed")[-4000:]
            raise CloudTrainError(f"SSH failed ({proc.returncode}): {detail}")
        return proc.stdout or ""
    finally:
        if key_path and key_path.exists():
            key_path.unlink(missing_ok=True)


def scp_to_remote(config: CloudSshConfig, local_path: Path, remote_path: str) -> None:
    if config.uses_password:
        from voice_platform.cloud_train.paramiko_transport import scp_to_remote_password

        scp_to_remote_password(config, local_path, remote_path)
        return
    _scp_openssh(config, local_path, remote_path, upload=True)


def scp_from_remote(config: CloudSshConfig, remote_path: str, local_path: Path) -> None:
    if config.uses_password:
        from voice_platform.cloud_train.paramiko_transport import scp_from_remote_password

        scp_from_remote_password(config, remote_path, local_path)
        return
    _scp_openssh(config, local_path, remote_path, upload=False)


def upload_directory(config: CloudSshConfig, local_dir: Path, remote_dir: str) -> None:
    """Pack local_dir as tar.gz, upload, and extract on remote (saves vs raw wav upload)."""
    local_dir = local_dir.resolve()
    if not local_dir.is_dir():
        raise CloudTrainError(f"Local dataset dir missing: {local_dir}")

    remote_dir = remote_dir.rstrip("/")
    remote_tar = f"{remote_dir}/upload.tar.gz"
    ssh_exec(config, f"mkdir -p {shlex.quote(remote_dir)}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tf:
        tar_path = Path(tf.name)
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(local_dir, arcname=".")
        scp_to_remote(config, tar_path, remote_tar)
        ssh_exec(
            config,
            f"cd {shlex.quote(remote_dir)} && tar xzf upload.tar.gz && rm -f upload.tar.gz",
            timeout_sec=600,
        )
    finally:
        tar_path.unlink(missing_ok=True)


def _scp_openssh(config: CloudSshConfig, local_path: Path, remote_path: str, *, upload: bool) -> None:
    key_path: Path | None = None
    if config.private_key_pem:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8")
        tmp.write(config.private_key_pem)
        tmp.flush()
        tmp.close()
        key_path = Path(tmp.name)
    target = f"{_ssh_target(config)}:{remote_path}"
    if upload:
        cmd = ["scp", *_openssh_common_args(config, key_path=key_path), str(local_path), target]
    else:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["scp", *_openssh_common_args(config, key_path=key_path), target, str(local_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if key_path:
        key_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "scp failed")[-4000:]
        raise CloudTrainError(f"SCP failed: {detail}")
