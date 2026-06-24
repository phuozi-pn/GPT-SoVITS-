"""Quick clone long-audio ref selection."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from workers.train.quick_clone_adapter import QuickCloneTrainAdapter

JOB = uuid4()
VOICE = uuid4()
OWNER = UUID("00000000-0000-0000-0000-000000000001")
ASSET = uuid4()


def _wav_bytes(duration_sec: float = 20.0, rate: int = 32000) -> bytes:
    buf = io.BytesIO()
    n = int(rate * duration_sec)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x01" * n)
    return buf.getvalue()


@patch("workers.train.quick_clone_adapter.VoiceVersionRepository")
@patch("workers.train.quick_clone_adapter.get_db_session")
@patch("voice_platform.storage.resolve.get_settings")
@patch("workers.train.quick_clone_adapter.get_settings")
def test_long_audio_uses_head_clip_not_random_slice(
    mock_gs, mock_resolve_gs, mock_session, mock_repo_cls, tmp_path
):
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    rel = f"{OWNER}/training/{ASSET}.wav"
    target = storage_root / rel
    target.parent.mkdir(parents=True)
    target.write_bytes(_wav_bytes(20.0))

    engine = tmp_path / "engine"
    (engine / "GPT_SoVITS" / "configs").mkdir(parents=True)
    (engine / "GPT_SoVITS" / "configs" / "tts_infer_v2pro.yaml").write_text(
        "v2Pro:\n  t2s_weights_path: a.ckpt\n  vits_weights_path: b.pth\n",
        encoding="utf-8",
    )

    mock_repo_cls.return_value.create_version.return_value = type(
        "Row",
        (),
        {"id": uuid4(), "checkpoint_uri": "x", "model_tag": MODEL_TAG_V2PRO, "version": 1},
    )()

    ref_text = "好好爱自己，就有人会爱你。"
    for gs in (mock_gs, mock_resolve_gs):
        gs.return_value.storage_root = str(storage_root)
        gs.return_value.engine_train_sample_text = ref_text
        gs.return_value.train_asr_language = "zh"
        gs.return_value.engine_train_platform_mount = "/workspace/GPT"
        gs.return_value.engine_train_root = str(engine)
        gs.return_value.engine_train_root_in_docker = "/workspace/GPT-SoVITS"

    QuickCloneTrainAdapter().run(
        payload=TrainPayload(
            voice_id=VOICE,
            voice_asset_id=ASSET,
            consent_id=uuid4(),
            model_tag=MODEL_TAG_V2PRO,
            asset_urls=[f"local://{rel}"],
            hyperparams={"ref_text": ref_text},
        ),
        owner_user_id=OWNER,
        job_id=JOB,
    )

    call_kw = mock_repo_cls.return_value.create_version.call_args.kwargs
    assert call_kw["ref_text"] == ref_text
    ref_path = Path(call_kw["metadata"]["engine_ref_audio_path"])
    assert ref_path.is_file()
    with wave.open(str(ref_path), "rb") as wf:
        dur = wf.getnframes() / float(wf.getframerate())
    assert 8.5 <= dur <= 9.1
