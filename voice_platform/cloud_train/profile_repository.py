from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.cloud_train.profile_models import UserCloudGpuProfileRow


class CloudGpuProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> UserCloudGpuProfileRow | None:
        return self._session.get(UserCloudGpuProfileRow, user_id)

    def upsert(
        self,
        *,
        user_id: UUID,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        auth_type: str,
        credential_enc: str,
        remote_engine_root: str,
        remote_platform_root: str,
        remote_work_dir: str,
    ) -> UserCloudGpuProfileRow:
        row = self.get(user_id)
        now = datetime.now(timezone.utc)
        if row is None:
            row = UserCloudGpuProfileRow(
                user_id=user_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                ssh_user=ssh_user,
                auth_type=auth_type,
                credential_enc=credential_enc,
                remote_engine_root=remote_engine_root,
                remote_platform_root=remote_platform_root,
                remote_work_dir=remote_work_dir,
            )
            self._session.add(row)
        else:
            row.ssh_host = ssh_host
            row.ssh_port = ssh_port
            row.ssh_user = ssh_user
            row.auth_type = auth_type
            row.credential_enc = credential_enc
            row.remote_engine_root = remote_engine_root
            row.remote_platform_root = remote_platform_root
            row.remote_work_dir = remote_work_dir
            row.updated_at = now
        self._session.flush()
        return row

    def mark_test(self, user_id: UUID, *, ok: bool) -> None:
        row = self.get(user_id)
        if not row:
            return
        row.last_tested_at = datetime.now(timezone.utc)
        row.last_test_ok = ok
        self._session.flush()

    def delete(self, user_id: UUID) -> bool:
        row = self.get(user_id)
        if not row:
            return False
        self._session.delete(row)
        self._session.flush()
        return True
