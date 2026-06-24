from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voice_platform.cloud_train.local_dataset import (
    prepare_local_cloud_dataset,
    rewrite_train_list_for_remote,
    write_train_list,
)
from voice_platform.engine.dataset_slice import slice_wav_into_segments


def _write_wav(path: Path, duration_sec: float, rate: int = 32000) -> None:
    n = int(duration_sec * rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x01\x00" * n)


def test_slice_wav_into_segments_long(tmp_path):
    wav = tmp_path / "long.wav"
    _write_wav(wav, 30.0)
    segs = slice_wav_into_segments(wav, tmp_path / "segments")
    assert len(segs) >= 2
    assert all(p.is_file() for p in segs)


def test_prepare_local_dataset_short_manual(tmp_path):
    wav = tmp_path / "short.wav"
    _write_wav(wav, 8.0)
    out = prepare_local_cloud_dataset(
        wav_path=wav,
        out_dir=tmp_path / "dataset",
        ref_text="你好，这是测试。",
        use_asr=False,
    )
    assert out.mode == "manual"
    assert out.segment_count == 1
    assert out.train_list.is_file()
    manifest = json.loads((out.dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["segment_count"] == 1


def test_prepare_local_dataset_long_asr(tmp_path):
    wav = tmp_path / "long.wav"
    _write_wav(wav, 24.0)
    mock_asr = MagicMock()
    mock_asr.is_available.return_value = True
    mock_asr.transcribe_segment.side_effect = lambda p: MagicMock(
        text=f"文本{Path(p).stem}",
        provider="mock",
        clip_sec=0.0,
    )
    with patch("voice_platform.cloud_train.local_dataset.AssetAsrService", return_value=mock_asr):
        out = prepare_local_cloud_dataset(
            wav_path=wav,
            out_dir=tmp_path / "dataset",
            ref_text="占位全文",
            use_asr=True,
        )
    assert out.mode == "asr"
    assert out.segment_count >= 2
    assert mock_asr.transcribe_segment.call_count == out.segment_count


def test_rewrite_train_list_for_remote(tmp_path):
    pairs = [(str(tmp_path / "segments" / "seg_0000.wav"), "你好")]
    write_train_list(
        pairs=pairs,
        list_path=tmp_path / "train.list",
        segments_prefix=str(tmp_path / "segments"),
        speaker="spk0",
        language="zh",
    )
    from voice_platform.cloud_train.local_dataset import PreparedLocalDataset

    prepared = PreparedLocalDataset(
        dataset_dir=tmp_path,
        segments_dir=tmp_path / "segments",
        train_list=tmp_path / "train.list",
        pairs=pairs,
        mode="asr",
        infer_ref_path=tmp_path / "segments" / "seg_0000.wav",
        infer_ref_text="你好",
        segment_count=1,
        segment_meta=[],
        enrich_mode="off",
    )
    rewrite_train_list_for_remote(prepared, remote_segments_dir="/root/jobs/x/dataset/segments")
    content = prepared.train_list.read_text(encoding="utf-8")
    assert content.startswith("/root/jobs/x/dataset/segments/seg_0000.wav|")
