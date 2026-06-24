from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

from domains.voices.import_service import engine_train_root_ready
from voice_platform.cloud_train.credentials import encrypt_credential
from voice_platform.cloud_train.profile_repository import CloudGpuProfileRepository
from voice_platform.cloud_train.remote_env import ensure_remote_train_environment
from voice_platform.cloud_train.ssh_client import CloudTrainError
from voice_platform.cloud_train.ssh_config import CloudSshConfig, config_from_env, config_from_profile
from voice_platform.config import get_settings

logger = logging.getLogger(__name__)


class CloudGpuProfileError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def resolve_ssh_config_for_user(session, user_id: UUID) -> CloudSshConfig:
    repo = CloudGpuProfileRepository(session)
    row = repo.get(user_id)
    if row:
        return config_from_profile(row)
    env_cfg = config_from_env()
    if env_cfg:
        return env_cfg
    raise CloudTrainError(
        "未配置云端 GPU 连接——请在 Studio 填写 SSH 主机、端口、密码并测试连接"
    )


class CloudGpuProfileService:
    def __init__(self, session) -> None:
        self._session = session
        self._repo = CloudGpuProfileRepository(session)
        self._settings = get_settings()

    def get_profile(self, user_id: UUID) -> dict | None:
        row = self._repo.get(user_id)
        if not row:
            return None
        return _public_profile(row, has_credential=True)

    def save_profile(
        self,
        *,
        user_id: UUID,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        password: str,
        remote_engine_root: str,
        remote_platform_root: str,
        remote_work_dir: str,
    ) -> dict:
        host = ssh_host.strip()
        if not host:
            raise CloudGpuProfileError("INVALID_HOST", "请填写 SSH 主机地址")
        existing = self._repo.get(user_id)
        pwd = password.strip()
        if pwd:
            credential_enc = encrypt_credential(pwd)
        elif existing:
            credential_enc = existing.credential_enc
        else:
            raise CloudGpuProfileError("PASSWORD_REQUIRED", "请填写 SSH 密码")
        row = self._repo.upsert(
            user_id=user_id,
            ssh_host=host,
            ssh_port=int(ssh_port or 22),
            ssh_user=(ssh_user or "root").strip() or "root",
            auth_type="password",
            credential_enc=credential_enc,
            remote_engine_root=(remote_engine_root or "/root/autodl-tmp/GPT-SoVITS").strip(),
            remote_platform_root=(remote_platform_root or "/root/autodl-tmp/GPT").strip(),
            remote_work_dir=(remote_work_dir or "/root/autodl-tmp/cloud_train_jobs").strip(),
        )
        self._session.commit()
        return _public_profile(row, has_credential=True)

    def test_connection(
        self,
        *,
        user_id: UUID,
        ssh_host: str | None = None,
        ssh_port: int | None = None,
        ssh_user: str | None = None,
        password: str | None = None,
        remote_engine_root: str | None = None,
        remote_platform_root: str | None = None,
    ) -> dict:
        config = self._build_test_config(
            user_id=user_id,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            password=password,
            remote_engine_root=remote_engine_root,
            remote_platform_root=remote_platform_root,
        )
        checks: list[dict] = []
        try:
            env = ensure_remote_train_environment(
                config,
                local_dataset_prep=True,
            )
            checks = list(env.checks)
            self._repo.mark_test(user_id, ok=True)
            self._session.commit()
            return {
                "ok": True,
                "message": "连接成功，脚本已同步，远端环境检查通过",
                "checks": checks,
                "python": env.python,
                "torch": env.torch_version,
            }
        except CloudTrainError as exc:
            if self._repo.get(user_id):
                self._repo.mark_test(user_id, ok=False)
                self._session.commit()
            return {"ok": False, "message": str(exc), "checks": checks}

    def delete_profile(self, user_id: UUID) -> None:
        if not self._repo.delete(user_id):
            raise CloudGpuProfileError("PROFILE_NOT_FOUND", "尚未保存云端连接", 404)
        self._session.commit()

    def _build_test_config(
        self,
        *,
        user_id: UUID,
        ssh_host: str | None,
        ssh_port: int | None,
        ssh_user: str | None,
        password: str | None,
        remote_engine_root: str | None,
        remote_platform_root: str | None,
    ) -> CloudSshConfig:
        row = self._repo.get(user_id)
        host = (ssh_host or (row.ssh_host if row else "") or "").strip()
        port = int(ssh_port or (row.ssh_port if row else 22) or 22)
        user = (ssh_user or (row.ssh_user if row else "root") or "root").strip()
        pwd = password
        if not pwd and row and row.auth_type == "password":
            from voice_platform.cloud_train.credentials import decrypt_credential

            pwd = decrypt_credential(row.credential_enc)
        if not host or not pwd:
            raise CloudGpuProfileError(
                "CREDENTIALS_INCOMPLETE",
                "请填写主机、端口、用户名和密码",
            )
        return CloudSshConfig(
            host=host,
            port=port,
            user=user,
            password=pwd,
            remote_engine_root=(remote_engine_root or (row.remote_engine_root if row else "") or "/root/autodl-tmp/GPT-SoVITS").strip(),
            remote_platform_root=(remote_platform_root or (row.remote_platform_root if row else "") or "/root/autodl-tmp/GPT").strip(),
            remote_work_dir=(row.remote_work_dir if row else "/root/autodl-tmp/cloud_train_jobs").strip(),
            timeout_sec=30,
        )


def user_can_cloud_train(session, user_id: UUID) -> bool:
    ok, _ = engine_train_root_ready()
    if not ok or get_settings().train_mock:
        return False
    row = CloudGpuProfileRepository(session).get(user_id)
    if row:
        return row.last_test_ok is True
    return config_from_env() is not None


def _public_profile(row, *, has_credential: bool) -> dict:
    return {
        "ssh_host": row.ssh_host,
        "ssh_port": row.ssh_port,
        "ssh_user": row.ssh_user,
        "auth_type": row.auth_type,
        "has_credential": has_credential,
        "remote_engine_root": row.remote_engine_root,
        "remote_platform_root": row.remote_platform_root,
        "remote_work_dir": row.remote_work_dir,
        "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
        "last_test_ok": row.last_test_ok,
    }
