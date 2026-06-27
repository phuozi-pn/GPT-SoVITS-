from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.assets.ref_text import align_ref_text_to_engine_ref


@patch("domains.assets.ref_text.AssetAsrService")
def test_align_ref_text_uses_asr_when_available(mock_svc_cls, tmp_path: Path):
    wav = tmp_path / "ref.wav"
    wav.write_bytes(b"x")
    mock_svc_cls.return_value.is_available.return_value = True
    mock_svc_cls.return_value.transcribe_segment.return_value = MagicMock(
        text="  前九秒台词  ",
        provider="mock",
        clip_sec=0.0,
    )

    text, aligned = align_ref_text_to_engine_ref(wav, fallback="整段长稿与音频不符")

    assert aligned is True
    assert text == "前九秒台词"


@patch("domains.assets.ref_text.AssetAsrService")
def test_align_ref_text_falls_back_when_asr_fails(mock_svc_cls, tmp_path: Path):
    wav = tmp_path / "ref.wav"
    wav.write_bytes(b"x")
    mock_svc_cls.return_value.is_available.return_value = True
    mock_svc_cls.return_value.transcribe_segment.side_effect = RuntimeError("asr down")

    text, aligned = align_ref_text_to_engine_ref(wav, fallback="手动参考文本")

    assert aligned is False
    assert text == "手动参考文本"
