from __future__ import annotations

from uuid import UUID

import pytest

from voice_platform.job.schemas import InferPayload, InferSegment, SynthesisRequest


VOICE_A = UUID("11111111-1111-1111-1111-111111111101")
VOICE_B = UUID("22222222-2222-2222-2222-222222222202")


def test_infer_payload_single_mode():
    p = InferPayload(voice_version_id=VOICE_A, text="你好", speed_factor=1.1)
    assert p.billed_char_count() == 2
    assert p.segments is None


def test_infer_payload_multi_mode():
    p = InferPayload(
        segments=[
            InferSegment(voice_version_id=VOICE_A, text="甲"),
            InferSegment(voice_version_id=VOICE_B, text="乙"),
        ]
    )
    assert p.billed_char_count() == 2


def test_synthesis_request_requires_single_or_segments():
    with pytest.raises(ValueError):
        SynthesisRequest()


def test_synthesis_request_with_tune_params():
    body = SynthesisRequest(
        voice_version_id=VOICE_A,
        text="你好",
        temperature=0.8,
        speed_factor=1.05,
    )
    assert body.temperature == 0.8
