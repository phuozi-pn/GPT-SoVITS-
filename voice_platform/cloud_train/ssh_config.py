from __future__ import annotations

from dataclasses import dataclass

from voice_platform.cloud_train.credentials import decrypt_credential
from voice_platform.cloud_train.profile_models import UserCloudGpuProfileRow
from voice_platform.config import Settings, get_settings


@dataclass(frozen=True)
class CloudSshConfig:
    host: str
    port: int
    user: str
    password: str | None = None
    private_key_pem: str | None = None
    remote_engine_root: str = "/root/autodl-tmp/GPT-SoVITS"
    remote_platform_root: str = "/root/autodl-tmp/GPT"
    remote_work_dir: str = "/root/autodl-tmp/cloud_train_jobs"
    timeout_sec: int = 7200

    @property
    def uses_password(self) -> bool:
        return bool(self.password)


def config_from_profile(row: UserCloudGpuProfileRow, *, settings: Settings | None = None) -> CloudSshConfig:
    settings = settings or get_settings()
    secret = decrypt_credential(row.credential_enc)
    password = secret if row.auth_type == "password" else None
    private_key_pem = secret if row.auth_type == "private_key" else None
    return CloudSshConfig(
        host=row.ssh_host.strip(),
        port=int(row.ssh_port or 22),
        user=(row.ssh_user or "root").strip() or "root",
        password=password,
        private_key_pem=private_key_pem,
        remote_engine_root=(row.remote_engine_root or "/root/autodl-tmp/GPT-SoVITS").strip(),
        remote_platform_root=(row.remote_platform_root or "/root/autodl-tmp/GPT").strip(),
        remote_work_dir=(row.remote_work_dir or "/root/autodl-tmp/cloud_train_jobs").strip(),
        timeout_sec=int(settings.cloud_train_ssh_timeout_sec or 7200),
    )


def config_from_env(settings: Settings | None = None) -> CloudSshConfig | None:
    settings = settings or get_settings()
    if not settings.cloud_train_enabled:
        return None
    host = (settings.cloud_train_ssh_host or "").strip()
    if not host:
        return None
    password = None
    private_key_pem = None
    key_path = (settings.cloud_train_ssh_key_path or "").strip()
    if key_path:
        from pathlib import Path

        pem = Path(key_path).expanduser().read_text(encoding="utf-8")
        private_key_pem = pem
    return CloudSshConfig(
        host=host,
        port=int(settings.cloud_train_ssh_port or 22),
        user=(settings.cloud_train_ssh_user or "root").strip() or "root",
        password=password,
        private_key_pem=private_key_pem,
        remote_engine_root=(settings.cloud_train_remote_engine_root or "/root/autodl-tmp/GPT-SoVITS").strip(),
        remote_platform_root=(settings.cloud_train_remote_platform_root or "/root/autodl-tmp/GPT").strip(),
        remote_work_dir=(settings.cloud_train_remote_work_dir or "/root/autodl-tmp/cloud_train_jobs").strip(),
        timeout_sec=int(settings.cloud_train_ssh_timeout_sec or 7200),
    )
