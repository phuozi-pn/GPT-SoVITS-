"""Lightweight mel-spectral speaker embedding for REQ-006 (numpy, no torch)."""

from __future__ import annotations

import math
import struct
import wave
from io import BytesIO

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - guarded by optional dep
    raise ImportError(
        "numpy is required for real quality evaluation; "
        "install with: pip install voice-platform[quality]"
    ) from exc

TARGET_SR = 16_000
N_FFT = 512
HOP = 160
N_MELS = 40
FMIN = 80.0
FMAX = 7600.0


def _hz_to_mel(hz: float) -> float:
    return 2595.0 * math.log10(1.0 + hz / 700.0)


def _mel_to_hz(mel: float) -> float:
    return 700.0 * (10 ** (mel / 2595.0) - 1.0)


def _mel_filterbank(n_mels: int, n_fft: int, sr: int) -> np.ndarray:
    fft_freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    mel_min = _hz_to_mel(FMIN)
    mel_max = _hz_to_mel(min(FMAX, sr / 2))
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = np.array([_mel_to_hz(m) for m in mel_points])
    bins = np.floor((n_fft + 1) * hz_points / sr).astype(int)
    bank = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for i in range(n_mels):
        left, center, right = bins[i], bins[i + 1], bins[i + 2]
        if center <= left or right <= center:
            continue
        for j in range(left, center):
            if 0 <= j < bank.shape[1]:
                bank[i, j] = (j - left) / max(center - left, 1)
        for j in range(center, right):
            if 0 <= j < bank.shape[1]:
                bank[i, j] = (right - j) / max(right - center, 1)
    return bank


_MEL_BANK = _mel_filterbank(N_MELS, N_FFT, TARGET_SR)


def read_wav_mono(data: bytes, *, target_sr: int = TARGET_SR) -> np.ndarray:
    with wave.open(BytesIO(data), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if sw != 2:
        raise ValueError(f"unsupported wav sample width: {sw}")
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        samples = samples.reshape(-1, nch).mean(axis=1)
    if sr != target_sr:
        samples = _resample_linear(samples, sr, target_sr)
    return samples


def _resample_linear(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr or len(samples) == 0:
        return samples
    duration = len(samples) / orig_sr
    out_len = max(1, int(round(duration * target_sr)))
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=out_len, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)


def extract_embedding(wav_bytes: bytes) -> np.ndarray:
    """Return L2-normalized mel-mean vector (speaker-ish timbre proxy)."""
    samples = read_wav_mono(wav_bytes)
    if len(samples) < N_FFT:
        samples = np.pad(samples, (0, N_FFT - len(samples)))
    window = np.hanning(N_FFT).astype(np.float32)
    frames: list[np.ndarray] = []
    for start in range(0, len(samples) - N_FFT + 1, HOP):
        frame = samples[start : start + N_FFT] * window
        spec = np.abs(np.fft.rfft(frame)) ** 2
        mel = _MEL_BANK @ spec
        mel = np.log(mel + 1e-6)
        frames.append(mel)
    if not frames:
        vec = np.zeros(N_MELS, dtype=np.float32)
    else:
        vec = np.mean(np.stack(frames, axis=0), axis=0)
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec.astype(np.float32)


def cosine_similarity(a: bytes, b: bytes) -> float:
    va = extract_embedding(a)
    vb = extract_embedding(b)
    score = float(np.dot(va, vb))
    return round(max(0.0, min(1.0, score)), 4)


def make_test_tone_wav(*, freq_hz: float = 440.0, duration_sec: float = 0.5, sr: int = 16000) -> bytes:
    """Deterministic mono PCM wav for unit tests."""
    nframes = int(sr * duration_sec)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(nframes):
            val = int(8000 * math.sin(2 * math.pi * freq_hz * i / sr))
            wf.writeframes(struct.pack("<h", max(-32768, min(32767, val))))
    return buf.getvalue()
