from __future__ import annotations

import wave
from pathlib import Path

from voice_platform.engine.train_dataset import (
    parse_train_list,
    parse_train_list_line,
    pick_infer_reference,
    trim_wav_copy,
)


def _write_wav(path: Path, duration_sec: float, rate: int = 32000) -> None:
    n = int(duration_sec * rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x01\x00" * n)


def test_parse_train_list_line():
    line = "/tmp/a.wav|spk0|zh|你好世界"
    assert parse_train_list_line(line) == ("/tmp/a.wav", "你好世界")
    assert parse_train_list_line("") is None


def test_parse_train_list_multiline():
    content = "/a.wav|spk0|zh|第一句\n/b.wav|spk0|zh|第二句\n"
    pairs = parse_train_list(content)
    assert len(pairs) == 2
    assert pairs[0][1] == "第一句"


def test_pick_infer_reference_prefers_3_to_10s(tmp_path):
    short = tmp_path / "s2.wav"
    good = tmp_path / "s5.wav"
    long = tmp_path / "s20.wav"
    _write_wav(short, 2.0)
    _write_wav(good, 6.0)
    _write_wav(long, 20.0)
    path, text = pick_infer_reference(
        [(str(short), "短"), (str(good), "合适"), (str(long), "长")],
        out_dir=tmp_path,
    )
    assert Path(path).name.startswith("s5") or "ref_" in Path(path).name
    assert text in ("合适", "短", "长")


def test_trim_wav_copy(tmp_path):
    src = tmp_path / "src.wav"
    dst = tmp_path / "dst.wav"
    _write_wav(src, 15.0)
    trim_wav_copy(src, dst, max_sec=9.0)
    with wave.open(str(dst), "rb") as wf:
        dur = wf.getnframes() / wf.getframerate()
    assert 8.9 <= dur <= 9.1
