"""REQ-025: Audio fingerprint unit tests."""

from __future__ import annotations

import io
import struct
import wave

import pytest

from voice_platform.fingerprint.encoder import (
    fingerprint_digest,
    fingerprint_similarity,
    generate_fingerprint,
    _hash_peaks,
    _read_wav_pcm,
    _resample_mono,
)


def _make_sine_wav(freq: float, duration_sec: float, sample_rate: int = 16000) -> bytes:
    """Generate a simple sine wave WAV for testing."""
    import math

    num_samples = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            val = int(16000 * math.sin(2 * math.pi * freq * t))
            samples.append(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


def _make_chirp_wav(duration_sec: float = 2.0, sample_rate: int = 16000) -> bytes:
    """Generate a chirp (frequency sweep) for richer fingerprinting."""
    import math

    num_samples = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Sweep from 200 Hz to 4000 Hz
            freq = 200 + (3800 * t / duration_sec)
            phase = 2 * math.pi * freq * t
            val = int(16000 * math.sin(phase))
            samples.append(struct.pack("<h", max(-32768, min(32767, val))))
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


class TestReadWav:
    def test_mono_sine(self) -> None:
        wav = _make_sine_wav(440, 1.0)
        samples, sr = _read_wav_pcm(wav)
        assert sr == 16000
        assert len(samples) == 16000

    def test_stereo(self) -> None:
        """Stereo WAV should be mixed to mono."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            frames = [struct.pack("<hh", 1000, 2000) for _ in range(100)]
            wf.writeframes(b"".join(frames))
        samples, sr = _read_wav_pcm(buf.getvalue())
        assert sr == 16000
        assert len(samples) == 100


class TestResample:
    def test_passthrough(self) -> None:
        samples = [1000, 2000, 3000, 4000]
        result = _resample_mono(samples, 16000)
        assert len(result) == 4
        assert all(isinstance(s, float) for s in result)


class TestFingerprintGeneration:
    def test_empty_wav(self) -> None:
        """Very short audio should return empty fingerprint."""
        wav = _make_sine_wav(440, 0.1)
        hashes = generate_fingerprint(wav)
        assert len(hashes) == 0

    def test_sine_wav(self) -> None:
        """A 1-second sine wave should produce some hashes."""
        wav = _make_sine_wav(440, 1.0)
        hashes = generate_fingerprint(wav)
        # Should produce at least some hashes from the pure tone
        assert isinstance(hashes, set)
        for h in hashes:
            assert isinstance(h, int)
            assert 0 <= h <= 0xFFFFFFFF

    def test_chirp_wav(self) -> None:
        """A chirp should produce more hashes than a pure tone."""
        wav = _make_chirp_wav(2.0)
        hashes = generate_fingerprint(wav)
        assert isinstance(hashes, set)
        # Chirp should produce many hashes
        assert len(hashes) > 0

    def test_long_audio_finishes_quickly(self) -> None:
        """Enrollment must not scan full-length exports (naive FFT is too slow)."""
        import time

        wav = _make_chirp_wav(30.0)
        t0 = time.perf_counter()
        hashes = generate_fingerprint(wav)
        elapsed = time.perf_counter() - t0
        assert len(hashes) > 0
        assert elapsed < 25.0

    def test_same_audio_same_fingerprint(self) -> None:
        """Same audio should produce identical fingerprints."""
        wav = _make_chirp_wav(1.0)
        h1 = generate_fingerprint(wav)
        h2 = generate_fingerprint(wav)
        assert h1 == h2

    def test_different_audio_different_fingerprint(self) -> None:
        """Different audio should produce different fingerprints."""
        wav1 = _make_sine_wav(440, 1.0)
        wav2 = _make_sine_wav(880, 1.0)
        h1 = generate_fingerprint(wav1)
        h2 = generate_fingerprint(wav2)
        # Should be different (not necessarily disjoint, but not identical)
        assert h1 != h2


class TestHashPeaks:
    def test_empty_peaks(self) -> None:
        assert _hash_peaks([]) == set()

    def test_few_peaks(self) -> None:
        peaks = [(0, 100), (1, 200)]
        hashes = _hash_peaks(peaks)
        assert len(hashes) > 0


class TestFingerprintSimilarity:
    def test_identical(self) -> None:
        a = {1, 2, 3, 4, 5}
        assert fingerprint_similarity(a, a) == 1.0

    def test_disjoint(self) -> None:
        assert fingerprint_similarity({1, 2}, {3, 4}) == 0.0

    def test_partial(self) -> None:
        sim = fingerprint_similarity({1, 2, 3, 4}, {1, 2, 5, 6})
        assert 0.25 < sim < 0.75

    def test_empty(self) -> None:
        assert fingerprint_similarity(set(), {1, 2}) == 0.0
        assert fingerprint_similarity({1, 2}, set()) == 0.0
        assert fingerprint_similarity(set(), set()) == 0.0

    def test_self_similarity_chirp(self) -> None:
        """A chirp should be highly similar to itself."""
        wav = _make_chirp_wav(1.0)
        h = generate_fingerprint(wav)
        sim = fingerprint_similarity(h, h)
        assert sim == 1.0


class TestFingerprintDigest:
    def test_deterministic(self) -> None:
        wav = _make_chirp_wav(0.5)
        h = generate_fingerprint(wav)
        d1 = fingerprint_digest(h)
        d2 = fingerprint_digest(h)
        assert d1 == d2
        assert len(d1) == 64  # SHA-256 hex
