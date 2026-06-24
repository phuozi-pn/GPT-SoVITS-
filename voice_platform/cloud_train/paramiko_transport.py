from __future__ import annotations

import logging
from pathlib import Path

import paramiko

from voice_platform.cloud_train.ssh_client import CloudTrainError
from voice_platform.cloud_train.ssh_config import CloudSshConfig

logger = logging.getLogger(__name__)


def _connect(config: CloudSshConfig) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs: dict = {
        "hostname": config.host,
        "port": config.port,
        "username": config.user,
        "timeout": 30,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if config.password:
        kwargs["password"] = config.password
    elif config.private_key_pem:
        try:
            kwargs["pkey"] = paramiko.Ed25519Key.from_private_key(
                __import__("io").StringIO(config.private_key_pem)
            )
        except paramiko.SSHException:
            try:
                kwargs["pkey"] = paramiko.RSAKey.from_private_key(
                    __import__("io").StringIO(config.private_key_pem)
                )
            except paramiko.SSHException as exc:
                raise CloudTrainError(f"Invalid private key: {exc}") from exc
    else:
        raise CloudTrainError("SSH password or private key required")
    client.connect(**kwargs)
    return client


def ssh_exec_password(config: CloudSshConfig, remote_cmd: str, *, timeout_sec: int | None = None) -> str:
    logger.info("cloud_train paramiko ssh: %s", remote_cmd[:200])
    client = _connect(config)
    try:
        _stdin, stdout, stderr = client.exec_command(remote_cmd, timeout=timeout_sec or config.timeout_sec)
        code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if code != 0:
            detail = (err or out or "ssh failed")[-4000:]
            raise CloudTrainError(f"SSH failed ({code}): {detail}")
        return out
    finally:
        client.close()


def scp_to_remote_password(config: CloudSshConfig, local_path: Path, remote_path: str) -> None:
    client = _connect(config)
    try:
        with client.open_sftp() as sftp:
            sftp.put(str(local_path), remote_path)
    finally:
        client.close()


def scp_from_remote_password(config: CloudSshConfig, remote_path: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = _connect(config)
    try:
        with client.open_sftp() as sftp:
            sftp.get(remote_path, str(local_path))
    finally:
        client.close()
