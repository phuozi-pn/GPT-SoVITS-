from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

from voice_platform.job.schemas import InferPayload, InferSegment
from workers.infer.runner import MockEngineAdapter, synthesize_payload

VOICE = UUID("11111111-1111-1111-1111-111111111101")


def test_synthesize_payload_multi_segment_concat():
    session = MagicMock()
    voice_row = MagicMock()
    voice_row.metadata_json = {}
    voice_row.ref_text = "ref"
    voice_row.ref_audio_uri = "/ref.wav"
    session.get.return_value = voice_row

    payload = InferPayload(
        segments=[
            InferSegment(voice_version_id=VOICE, text="甲", pitch_factor=1.0),
            InferSegment(voice_version_id=VOICE, text="乙", pitch_factor=1.0),
        ]
    )
    adapter = MockEngineAdapter()
    wav = synthesize_payload(
        adapter=adapter,
        session=session,
        job_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        owner_user_id=UUID("00000000-0000-0000-0000-000000000001"),
        payload=payload,
    )
    assert len(wav) > 44
    assert session.get.call_count == 2
