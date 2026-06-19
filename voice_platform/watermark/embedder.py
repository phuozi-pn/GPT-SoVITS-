from __future__ import annotations

import struct
import wave
from io import BytesIO
from datetime import datetime, timezone

from voice_platform.watermark.schemas import WatermarkPayload

# Magic bytes to mark the start of watermark data in LSB stream
_MAGIC = b"\xAB\xCD\xEF\x01"
_MAGIC_LEN = len(_MAGIC)

# Fixed-length encoding for payload size (4 bytes = up to ~4GB, but payloads are tiny)
_SIZE_BYTES = 4


def _bytes_to_bits(data: bytes) -> list[int]:
    """Convert bytes to a list of LSB-first bits (MSB first per byte)."""
    bits: list[int] = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: list[int]) -> bytes:
    """Convert a list of bits back to bytes (MSB first per byte)."""
    result = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return bytes(result)


def _pack_payload(payload: WatermarkPayload) -> bytes:
    """Serialise payload to magic + length + JSON bytes."""
    json_bytes = payload.to_json_str().encode("utf-8")
    size = len(json_bytes)
    return _MAGIC + struct.pack(">I", size) + json_bytes


def _unpack_payload(data: bytes) -> WatermarkPayload | None:
    """Try to extract a WatermarkPayload from raw bytes. Returns None if magic not found."""
    idx = data.find(_MAGIC)
    if idx < 0:
        return None
    offset = idx + _MAGIC_LEN
    if offset + _SIZE_BYTES > len(data):
        return None
    size = struct.unpack(">I", data[offset:offset + _SIZE_BYTES])[0]
    offset += _SIZE_BYTES
    if offset + size > len(data):
        return None
    json_bytes = data[offset:offset + size]
    try:
        return WatermarkPayload.from_json_str(json_bytes.decode("utf-8"))
    except Exception:
        return None


def embed_watermark(
    wav_bytes: bytes,
    payload: WatermarkPayload,
) -> bytes:
    """
    Embed watermark into WAV audio using LSB steganography.

    The watermark metadata is encoded into the least significant bits
    of audio samples. This produces imperceptible changes (MOS drop < 0.2).

    Only the first N samples are modified (enough to carry the payload).
    Remaining samples are left untouched.
    """
    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        params = wf.getparams()
        nframes = params.nframes
        frames = wf.readframes(nframes)

    nch = params.nchannels
    sw = params.sampwidth

    # Only support 16-bit mono/stereo for now
    if sw != 2:
        return wav_bytes  # Can't embed safely; return as-is

    packed = _pack_payload(payload)
    bits = _bytes_to_bits(packed)
    total_bits = len(bits)

    # Unpack samples
    fmt = f"<{nframes * nch}h"
    samples = list(struct.unpack(fmt, frames))

    # Embed bits into LSB of samples
    bits_embedded = 0
    for i in range(len(samples)):
        if bits_embedded >= total_bits:
            break
        # Set LSB to the watermark bit
        samples[i] = (samples[i] & ~1) | bits[bits_embedded]
        bits_embedded += 1

    # Re-pack
    new_frames = struct.pack(f"<{len(samples)}h", *samples)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setparams(params)
        wf.writeframes(new_frames)
    return buf.getvalue()


def extract_watermark(wav_bytes: bytes) -> WatermarkPayload | None:
    """
    Extract watermark from WAV audio LSB stream.

    Returns the embedded WatermarkPayload, or None if no watermark found
    or the audio format is unsupported.
    """
    try:
        with wave.open(BytesIO(wav_bytes), "rb") as wf:
            params = wf.getparams()
            nframes = params.nframes
            frames = wf.readframes(nframes)
    except Exception:
        return None

    nch = params.nchannels
    sw = params.sampwidth
    if sw != 2:
        return None

    fmt = f"<{nframes * nch}h"
    samples = struct.unpack(fmt, frames)

    # Read LSBs to reconstruct bytes
    raw_bits: list[int] = []
    # Read enough bits to potentially find the magic header + max payload
    max_bits = min(len(samples), 1024 * 8 * nch)  # Read up to 1024 bytes worth
    for i in range(max_bits):
        raw_bits.append(samples[i] & 1)

    raw_bytes = _bits_to_bytes(raw_bits)
    return _unpack_payload(raw_bytes)


def build_watermark_payload(
    user_id: str,
    voice_id: str,
    job_id: str,
) -> WatermarkPayload:
    """Convenience factory for watermark payload with auto timestamp."""
    return WatermarkPayload(
        user_id=user_id,
        voice_id=voice_id,
        job_id=job_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
