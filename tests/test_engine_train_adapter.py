from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from voice_platform.config import get_settings
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from workers.train.engine_adapter import EngineTrainAdapter

JOB = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER = UUID("00000000-0000-0000-0000-000000000001")
VOICE = UUID("11111111-1111-1111-1111-111111111100")


@pytest.fixture
def payload():
    return TrainPayload(
        voice_id=VOICE,
        voice_asset_id=UUID("33333333-3333-3333-3333-333333333301"),
        consent_id=UUID("22222222-2222-2222-2222-222222222201"),
        model_tag=MODEL_TAG_V2PRO,
        asset_urls=["engine://samples/ref_zh_zero_shot.wav"],
    )


def test_resolve_asset_fallback_sample(payload, tmp_path, monkeypatch):
    sample = tmp_path / "ref.wav"
    sample.write_bytes(b"RIFF")
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(tmp_path))
    get_settings.cache_clear()

    adapter = EngineTrainAdapter()
    with patch.object(adapter, "_platform_root", tmp_path):
        with patch.object(
            EngineTrainAdapter,
            "_resolve_asset",
            wraps=adapter._resolve_asset,
        ):
            # engine path missing -> fallback under infra/engine/samples
            infra_sample = tmp_path / "infra" / "engine" / "samples" / "ref_zh_zero_shot.wav"
            infra_sample.parent.mkdir(parents=True)
            infra_sample.write_bytes(b"RIFF")
            wav, text = adapter._resolve_asset(payload)
            assert wav == str(infra_sample.resolve())
            assert "测试" in text
    get_settings.cache_clear()


def test_run_creates_voice_version(payload, tmp_path, monkeypatch):
    engine_root = tmp_path / "engine"
    engine_root.mkdir()
    (engine_root / "webui.py").write_text("# stub", encoding="utf-8")
    staging = engine_root / "logs" / "platform_staging" / str(JOB)
    staging.mkdir(parents=True)
    result = {
        "gpt_checkpoint": "GPT_weights_v2Pro/pf_test.ckpt",
        "sovits_checkpoint": "SoVITS_weights_v2Pro/pf_test.pth",
        "elapsed_sec": 12.3,
        "gpt_epochs": 4,
        "sovits_epochs": 4,
    }
    (staging / "result.json").write_text(json.dumps(result), encoding="utf-8")

    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine_root))
    get_settings.cache_clear()

    import wave

    ref_wav = tmp_path / "ref.wav"
    with wave.open(str(ref_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 22050)

    adapter = EngineTrainAdapter()
    with patch.object(adapter, "_resolve_asset", return_value=(str(ref_wav), "你好")):
        with patch.object(adapter, "_invoke"):
            with patch("workers.train.engine_adapter.VoiceVersionRepository") as repo_cls:
                row = MagicMock()
                row.id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
                row.checkpoint_uri = "engine://SoVITS_weights_v2Pro/pf_test.pth"
                row.model_tag = MODEL_TAG_V2PRO
                row.version = 2
                repo_cls.return_value.create_version.return_value = row
                with patch("workers.train.engine_adapter.get_db_session") as sess:
                    sess.return_value = MagicMock()
                    out = adapter.run(payload=payload, owner_user_id=USER, job_id=JOB)

    assert out["voice_version_id"] == str(row.id)
    assert "engine_sovits_path" in out
    get_settings.cache_clear()
