"""Speaker embedding unit tests."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from voice_platform.quality.eval_sentences import EVAL_SENTENCES_ZH
from voice_platform.quality.speaker_embedding import (
    cosine_similarity,
    extract_embedding,
    make_test_tone_wav,
)


def test_eval_sentences_has_twenty():
    assert len(EVAL_SENTENCES_ZH) == 20


def test_identical_wav_high_similarity():
    wav = make_test_tone_wav(freq_hz=220.0)
    score = cosine_similarity(wav, wav)
    assert score >= 0.99


def test_different_tone_lower_similarity():
    a = make_test_tone_wav(freq_hz=220.0)
    b = make_test_tone_wav(freq_hz=880.0)
    same = cosine_similarity(a, a)
    diff = cosine_similarity(a, b)
    assert diff < same
    assert 0.0 <= diff <= 1.0


def test_extract_embedding_normalized():
    wav = make_test_tone_wav()
    vec = extract_embedding(wav)
    assert vec.shape == (40,)
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-4
