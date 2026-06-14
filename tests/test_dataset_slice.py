from __future__ import annotations

import io
import wave
from pathlib import Path

from voice_platform.engine.dataset_slice import bucket_sentences, slice_wav_dataset, split_sentences


def _write_wav(path: Path, duration_sec: float, rate: int = 22050) -> None:
    n = int(duration_sec * rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x01\x00" * n)


def test_split_sentences():
    s = split_sentences("第一句。第二句！第三句？")
    assert len(s) == 3


def test_slice_long_wav(tmp_path):
    wav = tmp_path / "long.wav"
    _write_wav(wav, 30.0)
    text = "。".join(f"第{i}句内容较长一些" for i in range(20)) + "。"
    pairs = slice_wav_dataset(wav_path=wav, ref_text=text, out_dir=tmp_path / "seg")
    assert len(pairs) >= 2
    for path, seg_text in pairs:
        assert Path(path).is_file()
        assert seg_text


def test_short_wav_single_segment(tmp_path):
    wav = tmp_path / "short.wav"
    _write_wav(wav, 5.0)
    pairs = slice_wav_dataset(wav_path=wav, ref_text="短文本。", out_dir=tmp_path / "seg")
    assert len(pairs) == 1
