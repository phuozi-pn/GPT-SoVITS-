from __future__ import annotations

import struct
import wave
from io import BytesIO

from voice_platform.audio_util import concat_wav, pitch_shift_wav


def _tone_wav(*, frames: int = 8000, rate: int = 32000) -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for i in range(frames):
            val = 4000 if i % 200 < 100 else -4000
            wf.writeframes(struct.pack("<h", val))
    return buf.getvalue()


def test_concat_wav_doubles_length():
    chunk = _tone_wav(frames=1000)
    merged = concat_wav([chunk, chunk])
    with wave.open(BytesIO(merged), "rb") as wf:
        assert wf.getnframes() == 2000


def test_pitch_shift_changes_frame_count():
    chunk = _tone_wav(frames=4000)
    shifted = pitch_shift_wav(chunk, 1.2)
    with wave.open(BytesIO(shifted), "rb") as wf:
        assert wf.getnframes() < 4000
