from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from voice_platform.cloud_train.config import is_cloud_train_configured
from voice_platform.cloud_train.orchestrator import CloudTrainOrchestrator
from voice_platform.cloud_train.ssh_config import CloudSshConfig
from workers.train.mode import build_train_adapter, resolve_train_mode, train_mode_description


def test_is_cloud_train_configured_requires_host():
    class S:
        cloud_train_enabled = True
        cloud_train_ssh_host = ""
        cloud_train_ssh_key_path = ""

    assert is_cloud_train_configured(S()) is False


def test_is_cloud_train_configured_ok():
    class S:
        cloud_train_enabled = True
        cloud_train_ssh_host = "gpu.example.com"
        cloud_train_ssh_key_path = ""

    assert is_cloud_train_configured(S()) is True


def test_resolve_train_mode_quick_explicit_over_engine_root(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    engine.mkdir()
    monkeypatch.setenv("TRAIN_MOCK", "false")
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    with patch("workers.train.mode.get_settings") as gs:
        gs.return_value.train_mode = "auto"
        gs.return_value.train_mock = False
        gs.return_value.engine_train_root = str(engine)
        assert resolve_train_mode(train_backend="quick") == "quick"


def test_resolve_train_mode_cloud_from_hyperparams(monkeypatch):
    monkeypatch.setenv("TRAIN_MOCK", "false")
    with patch("workers.train.mode.get_settings") as gs:
        gs.return_value.train_mode = "quick"
        gs.return_value.train_mock = False
        gs.return_value.engine_train_root = ""
        assert resolve_train_mode(train_backend="cloud") == "cloud"


def test_resolve_train_mode_cloud_without_global_env(monkeypatch):
    """Studio 自服务：用户 DB 凭证即可，不依赖 CLOUD_TRAIN_SSH_HOST。"""
    monkeypatch.setenv("TRAIN_MOCK", "false")
    with patch("workers.train.mode.get_settings") as gs:
        gs.return_value.train_mode = "quick"
        gs.return_value.train_mock = False
        gs.return_value.engine_train_root = ""
        gs.return_value.cloud_train_enabled = False
        gs.return_value.cloud_train_ssh_host = ""
        adapter, mode = build_train_adapter(hyperparams={"train_backend": "cloud"})
        assert mode == "cloud"
        assert adapter.__class__.__name__ == "CloudTrainAdapter"


def test_train_mode_description_cloud():
    assert "云端" in train_mode_description("cloud")


def test_cloud_orchestrator_pulls_weights(tmp_path, monkeypatch):
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"RIFF")
    job_id = "job-abc"

    result = {
        "gpt_checkpoint": "GPT_weights_v2Pro/cloud_job.ckpt",
        "sovits_checkpoint": "SoVITS_weights_v2Pro/cloud_job.pth",
        "exp_name": "cloud_job",
        "elapsed_sec": 120,
    }

    class S:
        storage_root = str(tmp_path / "storage")

    cfg = CloudSshConfig(
        host="h",
        port=22,
        user="root",
        password="secret",
        remote_engine_root="/root/GPT-SoVITS",
        remote_platform_root="/root/GPT",
        remote_work_dir="/root/jobs",
        timeout_sec=60,
    )

    gpt_bytes = b"gpt"
    sovits_bytes = b"sovits"

    def fake_ssh(settings, cmd, *, timeout_sec=None):
        if "exit_code" in cmd:
            return "0"
        return ""

    def fake_scp_up(settings, local, remote):
        assert local == wav

    def fake_scp_down(settings, remote, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        if remote.endswith("result.json"):
            local.write_text(json.dumps(result), encoding="utf-8")
        elif "GPT_weights" in remote:
            local.write_bytes(gpt_bytes)
        elif "SoVITS_weights" in remote:
            local.write_bytes(sovits_bytes)

    with patch("voice_platform.cloud_train.orchestrator.ssh_exec", fake_ssh):
        with patch("voice_platform.cloud_train.orchestrator.scp_to_remote", fake_scp_up):
            with patch("voice_platform.cloud_train.orchestrator.scp_from_remote", fake_scp_down):
                with patch(
                    "voice_platform.cloud_train.orchestrator.ensure_remote_train_environment",
                ) as ensure_env:
                    from voice_platform.cloud_train.remote_env import RemoteTrainEnvironment

                    ensure_env.return_value = RemoteTrainEnvironment(
                        python="/usr/bin/python3",
                        engine_root="/root/GPT-SoVITS",
                        platform_root="/root/GPT",
                        remote_work_dir="/root/jobs",
                        torch_version="2.1.0",
                        gpu_available=True,
                        checks=(),
                    )
                    out = CloudTrainOrchestrator(cfg, storage_root=S.storage_root).run(
                        local_wav=wav, job_id=job_id
                    )

    assert out.result["exp_name"] == "cloud_job"
    assert out.gpt_local.read_bytes() == gpt_bytes
    assert out.sovits_local.read_bytes() == sovits_bytes
    assert out.ref_wav_local.is_file()


def test_cloud_orchestrator_uploads_prepared_dataset(tmp_path, monkeypatch):
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"RIFF")
    job_id = "job-ds"

    from voice_platform.cloud_train.local_dataset import PreparedLocalDataset

    dataset_dir = tmp_path / "dataset"
    segments = dataset_dir / "segments"
    segments.mkdir(parents=True)
    seg = segments / "seg_0000.wav"
    seg.write_bytes(b"RIFF")
    list_file = dataset_dir / "train.list"
    list_file.write_text(f"{seg}|spk0|zh|hello\n", encoding="utf-8")
    prepared = PreparedLocalDataset(
        dataset_dir=dataset_dir,
        segments_dir=segments,
        train_list=list_file,
        pairs=[(str(seg), "hello")],
        mode="asr",
        infer_ref_path=seg,
        infer_ref_text="hello",
        segment_count=1,
        segment_meta=[],
        enrich_mode="off",
    )

    result = {
        "gpt_checkpoint": "GPT_weights_v2Pro/ds.ckpt",
        "sovits_checkpoint": "SoVITS_weights_v2Pro/ds.pth",
        "exp_name": "ds",
        "elapsed_sec": 60,
    }

    cfg = CloudSshConfig(
        host="h",
        port=22,
        user="root",
        password="secret",
        remote_engine_root="/root/GPT-SoVITS",
        remote_platform_root="/root/GPT",
        remote_work_dir="/root/jobs",
        timeout_sec=60,
    )

    uploads: list[str] = []

    def fake_ssh(settings, cmd, *, timeout_sec=None):
        uploads.append(cmd)
        if "exit_code" in cmd:
            return "0"
        return ""

    def fake_scp_up(settings, local, remote):
        pass

    def fake_upload(settings, local_dir, remote_dir):
        uploads.append(f"upload:{remote_dir}")

    def fake_scp_down(settings, remote, local):
        local.parent.mkdir(parents=True, exist_ok=True)
        if remote.endswith("result.json"):
            local.write_text(json.dumps(result), encoding="utf-8")
        else:
            local.write_bytes(b"w")

    with patch("voice_platform.cloud_train.orchestrator.ssh_exec", fake_ssh):
        with patch("voice_platform.cloud_train.orchestrator.scp_to_remote", fake_scp_up):
            with patch("voice_platform.cloud_train.orchestrator.upload_directory", fake_upload):
                with patch("voice_platform.cloud_train.orchestrator.scp_from_remote", fake_scp_down):
                    with patch(
                        "voice_platform.cloud_train.orchestrator.ensure_remote_train_environment",
                    ) as ensure_env:
                        from voice_platform.cloud_train.remote_env import RemoteTrainEnvironment

                        ensure_env.return_value = RemoteTrainEnvironment(
                            python="/usr/bin/python3",
                            engine_root="/root/GPT-SoVITS",
                            platform_root="/root/GPT",
                            remote_work_dir="/root/jobs",
                            torch_version="2.1.0",
                            gpu_available=True,
                            checks=(),
                        )
                        out = CloudTrainOrchestrator(cfg, storage_root=str(tmp_path / "storage")).run(
                            local_wav=wav,
                            job_id=job_id,
                            prepared_dataset=prepared,
                            remote_env=ensure_env.return_value,
                        )
    ensure_env.assert_not_called()

    assert any("train_from_dataset.sh" in u for u in uploads)
    assert any(u.startswith("upload:") for u in uploads)
    assert out.dataset_mode == "asr"
