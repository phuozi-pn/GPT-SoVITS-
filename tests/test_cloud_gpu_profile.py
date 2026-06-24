from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from domains.cloud_train.service import CloudGpuProfileError, CloudGpuProfileService, user_can_cloud_train


def _profile_row(*, last_test_ok: bool | None = True):
    return SimpleNamespace(
        user_id=uuid4(),
        ssh_host="connect.autodl.xyz",
        ssh_port=12345,
        ssh_user="root",
        auth_type="password",
        credential_enc="enc",
        remote_engine_root="/root/GPT-SoVITS",
        remote_platform_root="/root/GPT",
        remote_work_dir="/root/jobs",
        last_tested_at=datetime.now(timezone.utc),
        last_test_ok=last_test_ok,
    )


def test_save_profile_keeps_password_when_blank(monkeypatch):
    user_id = uuid4()
    row = _profile_row(last_test_ok=True)
    session = MagicMock()
    repo = MagicMock()
    repo.get.return_value = row
    repo.upsert.return_value = row

    with patch("domains.cloud_train.service.CloudGpuProfileRepository", return_value=repo), patch(
        "domains.cloud_train.service.encrypt_credential"
    ) as enc:
        svc = CloudGpuProfileService(session)
        out = svc.save_profile(
            user_id=user_id,
            ssh_host="new.host",
            ssh_port=22,
            ssh_user="root",
            password="",
            remote_engine_root="/root/GPT-SoVITS",
            remote_platform_root="/root/GPT",
            remote_work_dir="/root/jobs",
        )
    enc.assert_not_called()
    assert repo.upsert.call_args.kwargs["credential_enc"] == "enc"
    assert repo.upsert.call_args.kwargs["ssh_host"] == "new.host"


def test_save_profile_requires_password_for_new_user():
    session = MagicMock()
    repo = MagicMock()
    repo.get.return_value = None

    with patch("domains.cloud_train.service.CloudGpuProfileRepository", return_value=repo):
        svc = CloudGpuProfileService(session)
        with pytest.raises(CloudGpuProfileError) as exc:
            svc.save_profile(
                user_id=uuid4(),
                ssh_host="h",
                ssh_port=22,
                ssh_user="root",
                password="",
                remote_engine_root="/root/GPT-SoVITS",
                remote_platform_root="/root/GPT",
                remote_work_dir="/root/jobs",
            )
    assert exc.value.code == "PASSWORD_REQUIRED"


def test_user_can_cloud_train_requires_verified_profile(monkeypatch, tmp_path):
    engine = tmp_path / "engine"
    engine.mkdir()
    monkeypatch.setenv("TRAIN_MOCK", "false")
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    user_id = uuid4()
    session = MagicMock()
    repo = MagicMock()
    repo.get.return_value = _profile_row(last_test_ok=False)

    with patch("domains.cloud_train.service.CloudGpuProfileRepository", return_value=repo), patch(
        "domains.cloud_train.service.config_from_env", return_value=None
    ):
        assert user_can_cloud_train(session, user_id) is False

    repo.get.return_value = _profile_row(last_test_ok=True)
    with patch("domains.cloud_train.service.CloudGpuProfileRepository", return_value=repo), patch(
        "domains.cloud_train.service.config_from_env", return_value=None
    ):
        assert user_can_cloud_train(session, user_id) is True

    get_settings.cache_clear()
