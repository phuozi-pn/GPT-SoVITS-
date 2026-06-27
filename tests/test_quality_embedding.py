"""QualityService embedding evaluation (non-mock path)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

np = pytest.importorskip("numpy")

from domains.quality.service import QualityService
from voice_platform.quality.speaker_embedding import make_test_tone_wav

OWNER = UUID("00000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("11111111-1111-1111-1111-111111111101")


def test_embedding_evaluate_uses_synth_and_ref():
    ref_wav = make_test_tone_wav(freq_hz=300.0)
    synth_wav = make_test_tone_wav(freq_hz=305.0)

    ver = MagicMock()
    ver.owner_user_id = OWNER
    ver.ref_audio_uri = "local://u/ref.wav"
    ver.id = VERSION_ID

    session = MagicMock()
    svc = QualityService(session)
    svc._versions = MagicMock()
    svc._versions.get.return_value = ver
    svc._reports = MagicMock()
    svc._reports.upsert.return_value = MagicMock(
        voice_version_id=VERSION_ID,
        similarity_score=0.95,
        quality_pass=True,
        threshold=0.9,
        eval_sentence="hello",
        ref_audio_url="http://x/ref.wav",
        synth_audio_url="http://x/synth.wav",
        method="mel_speaker_embedding_v1",
        created_at=None,
        updated_at=None,
    )
    svc._votes = MagicMock()
    svc._votes.stats.return_value = (0, None)

    with patch("domains.quality.service.get_settings") as gs:
        gs.return_value.quality_mock = False
        gs.return_value.quality_similarity_threshold = 0.90
        gs.return_value.quality_eval_sentence_count = 1
        with patch("voice_platform.quality.engine_synth.load_ref_wav_bytes_for_voice", return_value=ref_wav):
            with patch(
                "voice_platform.quality.engine_synth.synthesize_eval_wav",
                return_value=synth_wav,
            ):
                with patch("domains.quality.service.LocalStorage") as storage_cls:
                    storage_cls.return_value.save_bytes.return_value = f"{OWNER}/quality/x.wav"
                    storage_cls.return_value.public_url.return_value = "http://x/synth.wav"
                    report = svc.evaluate(voice_version_id=VERSION_ID)

    assert report.method == "mel_speaker_embedding_v1"
    svc._reports.upsert.assert_called_once()
    call_kw = svc._reports.upsert.call_args.kwargs
    assert call_kw["method"] == "mel_speaker_embedding_v1"
    assert call_kw["similarity_score"] >= 0.5
