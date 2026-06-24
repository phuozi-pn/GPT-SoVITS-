from __future__ import annotations

from unittest.mock import patch

import pytest

from voice_platform.cloud_train.remote_env import ensure_remote_train_environment
from voice_platform.cloud_train.ssh_client import CloudTrainError
from voice_platform.cloud_train.ssh_config import CloudSshConfig


def _cfg() -> CloudSshConfig:
    return CloudSshConfig(
        host="h",
        port=22,
        user="root",
        password="secret",
        remote_engine_root="/root/autodl-tmp/GPT-SoVITS",
        remote_platform_root="/root/autodl-tmp/GPT",
        remote_work_dir="/root/autodl-tmp/jobs",
        timeout_sec=60,
    )


def test_ensure_remote_train_environment_syncs_and_validates():
    cfg = _cfg()
    calls: list[str] = []

    def fake_ssh(settings, cmd, *, timeout_sec=None):
        calls.append(cmd)
        if "echo ok" in cmd:
            return "ok\n"
        if "torch.__version__" in cmd:
            return "2.1.0\n"
        if "cuda.is_available" in cmd:
            return "1\n"
        if "command -v python3" in cmd or "miniconda3/bin/python3" in cmd:
            return "/root/miniconda3/bin/python3\n"
        return ""

    with patch("voice_platform.cloud_train.remote_env.ssh_exec", fake_ssh):
        with patch("voice_platform.cloud_train.remote_env.ensure_remote_train_scripts") as sync:
            with patch(
                "voice_platform.cloud_train.remote_env.resolve_remote_python",
                return_value="/root/miniconda3/bin/python3",
            ):
                env = ensure_remote_train_environment(cfg, local_dataset_prep=True)

    sync.assert_called_once()
    assert env.python == "/root/miniconda3/bin/python3"
    assert env.torch_version == "2.1.0"
    assert env.gpu_available is True
    assert any(c["name"] == "scripts" for c in env.checks)


def test_ensure_remote_train_environment_requires_gpu():
    cfg = _cfg()

    def fake_ssh(settings, cmd, *, timeout_sec=None):
        if "echo ok" in cmd:
            return "ok\n"
        if "torch.__version__" in cmd:
            return "2.1.0\n"
        if "cuda.is_available" in cmd:
            return "0\n"
        if "command -v python3" in cmd or "miniconda3/bin/python3" in cmd:
            return "/root/miniconda3/bin/python3\n"
        return ""

    with patch("voice_platform.cloud_train.remote_env.ssh_exec", fake_ssh):
        with patch("voice_platform.cloud_train.remote_env.ensure_remote_train_scripts"):
            with patch(
                "voice_platform.cloud_train.remote_env.resolve_remote_python",
                return_value="/root/miniconda3/bin/python3",
            ):
                with pytest.raises(CloudTrainError, match="GPU"):
                    ensure_remote_train_environment(cfg)
