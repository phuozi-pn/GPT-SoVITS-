"""
REQ-025: Audio fingerprint encoder — spectral peak hashing.

Generates compact fingerprints from WAV audio using:
1. FFT-based spectrogram
2. Peak detection in time-frequency domain
3. Combinatorial hashing of peak pairs (frequency, time delta)
4. Returns a set of 32-bit integer hashes for efficient storage and comparison

This is a simplified "constellation" approach inspired by Shazam's algorithm.
"""

from __future__ import annotations

import hashlib
import struct
import wave
from io import BytesIO

# ── Constants ────────────────────────────────────────────────
SAMPLE_RATE = 16000  # Downsample target for fingerprinting
FFT_SIZE = 2048
HOP_SIZE = 512  # ~32ms hop at 16kHz
PEAK_NEIGHBORHOOD_SIZE = 20  # freq bins for local maximum detection
TARGET_ZONE_MIN = 1  # minimum time delta (frames) for hash pairs
TARGET_ZONE_MAX = 63  # maximum time delta (frames) for hash pairs
FANOUT = 3  # number of peaks paired from each anchor
# Naive Python DFT is O(frames * fft^2); cap enroll clip to keep infer worker responsive.
MAX_FINGERPRINT_SEC = 2.0


def _read_wav_pcm(wav_bytes: bytes) -> tuple[list[int], int]:
    """Read WAV bytes and return PCM samples + original sample rate."""
    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        sr = wf.getframerate()
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    # Unpack to int samples
    if sampwidth == 2:
        fmt = f"<{nframes * nchannels}h"
        samples = list(struct.unpack(fmt, raw))
    elif sampwidth == 1:
        samples = [b - 128 for b in raw]
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Mix down to mono
    if nchannels > 1:
        mono = []
        for i in range(0, len(samples), nchannels):
            mono.append(sum(samples[i : i + nchannels]) // nchannels)
        samples = mono

    return samples, sr


def _resample_mono(samples: list[int], orig_sr: int, target_sr: int = SAMPLE_RATE) -> list[float]:
    """Simple linear resampling to target sample rate. Returns float samples."""
    if orig_sr == target_sr:
        return [s / 32768.0 for s in samples]

    ratio = orig_sr / target_sr
    out_len = int(len(samples) / ratio)
    result: list[float] = []
    for i in range(out_len):
        src_idx = i * ratio
        src_i = int(src_idx)
        frac = src_idx - src_i
        if src_i + 1 < len(samples):
            val = samples[src_i] * (1 - frac) + samples[src_i + 1] * frac
        else:
            val = samples[src_i]
        result.append(val / 32768.0)
    return result


def _hamming_window(size: int) -> list[float]:
    """Generate a Hamming window of given size."""
    import math

    return [0.54 - 0.46 * math.cos(2 * math.pi * i / (size - 1)) for i in range(size)]


def _fft_spectrogram(samples: list[float]) -> list[list[float]]:
    """Compute magnitude spectrogram using FFT with Hamming window."""
    import cmath  # noqa: F401
    import math

    window = _hamming_window(FFT_SIZE)
    num_frames = max(0, (len(samples) - FFT_SIZE) // HOP_SIZE) + 1
    spectrogram: list[list[float]] = []

    for frame_idx in range(num_frames):
        start = frame_idx * HOP_SIZE
        frame = [samples[start + i] * window[i] if start + i < len(samples) else 0.0 for i in range(FFT_SIZE)]

        # Naive DFT (avoid numpy dependency)
        mags: list[float] = []
        for k in range(FFT_SIZE // 2 + 1):
            real = 0.0
            imag = 0.0
            for n in range(FFT_SIZE):
                angle = -2 * math.pi * k * n / FFT_SIZE
                real += frame[n] * math.cos(angle)
                imag += frame[n] * math.sin(angle)
            mags.append(math.sqrt(real * real + imag * imag))
        spectrogram.append(mags)

    return spectrogram


def _find_peaks(spectrogram: list[list[float]], amp_min: float = 0.01) -> list[tuple[int, int]]:
    """
    Find local maxima in the spectrogram.
    Returns list of (time_frame, frequency_bin).
    """
    if not spectrogram:
        return []

    num_frames = len(spectrogram)
    num_bins = len(spectrogram[0])
    peaks: list[tuple[int, int]] = []

    for t in range(num_frames):
        for f in range(1, num_bins - 1):
            mag = spectrogram[t][f]
            if mag < amp_min:
                continue

            # Check local neighborhood in frequency
            f_start = max(1, f - PEAK_NEIGHBORHOOD_SIZE // 2)
            f_end = min(num_bins - 1, f + PEAK_NEIGHBORHOOD_SIZE // 2)
            is_peak = True
            for fn in range(f_start, f_end + 1):
                if fn == f:
                    continue
                if spectrogram[t][fn] >= mag:
                    is_peak = False
                    break

            if not is_peak:
                continue

            # Check adjacent time frames
            for dt in (-1, 1):
                tn = t + dt
                if 0 <= tn < num_frames:
                    for fn in range(max(1, f - 2), min(num_bins - 1, f + 3)):
                        if spectrogram[tn][fn] >= mag:
                            is_peak = False
                            break
                if not is_peak:
                    break

            if is_peak:
                peaks.append((t, f))

    return peaks


def _hash_peaks(peaks: list[tuple[int, int]]) -> set[int]:
    """
    Generate combinatorial hashes from peak pairs.
    Each hash encodes: anchor_freq (9 bits) | target_freq (9 bits) | time_delta (14 bits) = 32 bits
    """
    hashes: set[int] = set()
    num_peaks = len(peaks)

    for i in range(num_peaks):
        t_anchor, f_anchor = peaks[i]
        for j in range(1, min(FANOUT + 1, num_peaks - i)):
            t_target, f_target = peaks[i + j]
            dt = t_target - t_anchor
            if dt < TARGET_ZONE_MIN or dt > TARGET_ZONE_MAX:
                continue

            # Pack into 32-bit hash
            f1 = min(f_anchor, 511)  # 9 bits
            f2 = min(f_target, 511)  # 9 bits
            dt_clamped = min(dt, 16383)  # 14 bits
            h = (f1 << 23) | (f2 << 14) | dt_clamped
            hashes.add(h)

    return hashes


def generate_fingerprint(wav_bytes: bytes) -> set[int]:
    """
    Generate a set of 32-bit audio fingerprint hashes from WAV bytes.

    Returns empty set for audio shorter than ~1 second.
    """
    samples, orig_sr = _read_wav_pcm(wav_bytes)

    # Need at least ~0.5s of audio
    min_samples = int(orig_sr * 0.5)
    if len(samples) < min_samples:
        return set()

    float_samples = _resample_mono(samples, orig_sr)
    max_samples = int(SAMPLE_RATE * MAX_FINGERPRINT_SEC)
    if len(float_samples) > max_samples:
        float_samples = float_samples[:max_samples]
    spectrogram = _fft_spectrogram(float_samples)

    if len(spectrogram) < 5:
        return set()

    peaks = _find_peaks(spectrogram)
    if len(peaks) < 5:
        return set()

    return _hash_peaks(peaks)


def fingerprint_similarity(hashes_a: set[int], hashes_b: set[int]) -> float:
    """
    Compute Jaccard similarity between two fingerprint hash sets.
    Returns 0.0 - 1.0.
    """
    if not hashes_a or not hashes_b:
        return 0.0
    intersection = len(hashes_a & hashes_b)
    union = len(hashes_a | hashes_b)
    return intersection / union if union > 0 else 0.0


def fingerprint_digest(hashes: set[int]) -> str:
    """Return a stable hex digest for a fingerprint set (for storage/identity)."""
    sorted_hashes = sorted(hashes)
    data = b"".join(struct.pack("<I", h) for h in sorted_hashes)
    return hashlib.sha256(data).hexdigest()
