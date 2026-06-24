"""Quick clone train adapter tests."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from workers.train.mode import build_train_adapter, resolve_train_mode
from workers.train.quick_clone_adapter import QuickCloneTrainAdapter

JOB = uuid4()
VOICE = uuid4()
OWNER = UUID("00000000-0000-0000-0000-000000000001")
ASSET = uuid4()


def _wav_bytes(duration_sec: float = 6.0, rate: int = 32000) -> bytes:
    buf = io.BytesIO()
    n = int(rate * duration_sec)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x01" * n)
    return buf.getvalue()


def test_resolve_train_mode_quick_when_not_mock_and_no_engine_root(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIN_MOCK", "false")
    monkeypatch.setenv("TRAIN_MODE", "auto")
    with patch("workers.train.mode.get_settings") as gs:
        gs.return_value.train_mock = False
        gs.return_value.train_mode = "auto"
        gs.return_value.engine_train_root = str(tmp_path / "missing")
        assert resolve_train_mode() == "quick"


def test_build_train_adapter_quick(tmp_path):
    with patch("workers.train.mode.get_settings") as gs:
        gs.return_value.train_mock = False
        gs.return_value.train_mode = "auto"
        gs.return_value.engine_train_root = str(tmp_path / "missing")
        adapter, mode = build_train_adapter(use_mock=False)
    assert mode == "quick"
    assert isinstance(adapter, QuickCloneTrainAdapter)


@patch("voice_platform.storage.resolve.get_settings")
@patch("workers.train.quick_clone_adapter.VoiceVersionRepository")
@patch("workers.train.quick_clone_adapter.get_db_session")
def test_quick_clone_creates_version(mock_session, mock_repo_cls, mock_resolve_settings, tmp_path):
    wav_path = tmp_path / "asset.wav"
    wav_path.write_bytes(_wav_bytes(6.0))
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    rel = f"{OWNER}/training/{ASSET}.wav"
    target = storage_root / rel
    target.parent.mkdir(parents=True)
    target.write_bytes(wav_path.read_bytes())

    row = type("Row", (), {"id": uuid4(), "checkpoint_uri": "x", "model_tag": MODEL_TAG_V2PRO, "version": 1})()
    mock_repo_cls.return_value.create_version.return_value = row

    with patch("workers.train.quick_clone_adapter.get_settings") as gs:
        gs.return_value.storage_root = str(storage_root)
        gs.return_value.engine_train_sample_text = "测试参考文本用于快速克隆训练。"
        gs.return_value.train_asr_language = "zh"
        gs.return_value.engine_train_platform_mount = "/workspace/GPT"
        gs.return_value.engine_train_root = str(tmp_path / "engine")
        gs.return_value.engine_train_root_in_docker = "/workspace/GPT-SoVITS"
        (tmp_path / "engine" / "GPT_SoVITS" / "configs").mkdir(parents=True)
        (tmp_path / "engine" / "GPT_SoVITS" / "configs" / "tts_infer_v2pro.yaml").write_text(
            "v2Pro:\n  t2s_weights_path: GPT_SoVITS/pretrained_models/s1v3.ckpt\n"
            "  vits_weights_path: GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth\n",
            encoding="utf-8",
        )
        mock_resolve_settings.return_value.storage_root = str(storage_root)

        result = QuickCloneTrainAdapter().run(
            payload=TrainPayload(
                voice_id=VOICE,
                voice_asset_id=ASSET,
                consent_id=uuid4(),
                model_tag=MODEL_TAG_V2PRO,
                asset_urls=[f"local://{rel}"],
                hyperparams={"ref_text": "测试参考文本用于快速克隆训练。"},
            ),
            owner_user_id=OWNER,
            job_id=JOB,
        )

    assert result["train_mode"] == "quick_clone"
    mock_repo_cls.return_value.create_version.assert_called_once()
    call_kw = mock_repo_cls.return_value.create_version.call_args.kwargs
    assert call_kw["ref_text"]
    assert call_kw["metadata"]["train_mode"] == "quick_clone"
    assert call_kw["metadata"]["mock"] is False
    assert call_kw["metadata"]["engine_ref_audio_container"].endswith(f"{JOB}.wav")
    assert call_kw["metadata"]["engine_use_base_weights"] is True
    assert call_kw["metadata"]["engine_gpt_weights"]
    assert call_kw["metadata"]["engine_sovits_weights"]
