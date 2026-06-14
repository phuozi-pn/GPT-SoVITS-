from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import httpx

from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.schemas import InferPayload
from workers.infer.runner import EngineAdapter, InferContext

VOICE_ID = UUID("11111111-1111-1111-1111-111111111101")


def test_synthesize_sets_weights_before_tts():
    voice = VoiceVersionRow(
        id=VOICE_ID,
        voice_id=UUID("11111111-1111-1111-1111-111111111100"),
        owner_user_id=UUID("00000000-0000-0000-0000-000000000001"),
        version=1,
        model_tag="gsv-v2pro-20250606",
        ref_text="你好",
        metadata_json={
            "mock": False,
            "engine_gpt_weights": "GPT_weights_v2Pro/t.ckpt",
            "engine_sovits_weights": "SoVITS_weights_v2Pro/t.pth",
            "engine_ref_audio_path": "/workspace/GPT/data/storage/u/a.wav",
        },
    )
    ctx = InferContext(
        job_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        owner_user_id=UUID("00000000-0000-0000-0000-000000000001"),
        payload=InferPayload(voice_version_id=VOICE_ID, text="测试"),
        voice=voice,
    )
    adapter = EngineAdapter(base_url="http://127.0.0.1:9880")
    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, text="ok")

    def fake_post(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, content=b"RIFF")

    with patch.object(httpx.Client, "__enter__", return_value=MagicMock(get=fake_get, post=fake_post)):
        with patch.object(httpx.Client, "__exit__", return_value=False):
            adapter.synthesize(ctx)

    assert calls[0].endswith("/set_gpt_weights")
    assert calls[1].endswith("/set_sovits_weights")
    assert calls[2].endswith("/tts")
