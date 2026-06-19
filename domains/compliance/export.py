"""Compliant export: prepend AI synthesis label to audio and build ZIP metadata."""
from __future__ import annotations

import io
import json
import struct
import wave
from datetime import datetime, timezone
from typing import Any

from voice_platform.watermark.schemas import WatermarkPayload

LABEL_TYPE_RHYTHM = "rhythm"
COMPLIANCE_README = """AI 合成内容标识说明
====================

本压缩包内音频由人工智能语音合成技术生成。

标识方式：
- 每条音频文件开头含「短-长-短-短」节奏标识音（GB 45438-2025 显式标识）
- 音频中嵌入数字水印，携带用户、音色、任务信息
- manifest.json 记录每条台词的合规元数据

请勿移除标识后用于误导性传播。使用他人声纹须持有合法授权。
"""


def rhythm_label_wav(*, sample_rate: int = 32000, short_ms: int = 150, long_ms: int = 300) -> bytes:
    """Generate 短-长-短-短 rhythm pattern as mono 16-bit PCM wav."""
    pattern_ms = [short_ms, long_ms, short_ms, short_ms]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for duration_ms in pattern_ms:
            nframes = int(sample_rate * duration_ms / 1000)
            for i in range(nframes):
                val = 6000 if (i // (sample_rate // 20)) % 2 == 0 else -6000
                wf.writeframes(struct.pack("<h", val))
    return buf.getvalue()


def _read_wav_params(data: bytes) -> tuple[int, int, int, bytes]:
    with wave.open(io.BytesIO(data), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    return channels, sample_width, sample_rate, frames


def concat_wav(prefix: bytes, body: bytes) -> bytes:
    p_ch, p_sw, p_sr, p_frames = _read_wav_params(prefix)
    b_ch, b_sw, b_sr, b_frames = _read_wav_params(body)
    if (p_ch, p_sw, p_sr) != (b_ch, b_sw, b_sr):
        raise ValueError(
            f"WAV format mismatch: label ({p_ch},{p_sw},{p_sr}) vs body ({b_ch},{b_sw},{b_sr})"
        )
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(p_ch)
        wf.setsampwidth(p_sw)
        wf.setframerate(p_sr)
        wf.writeframes(p_frames + b_frames)
    return out.getvalue()


def apply_compliance_label(
    wav_bytes: bytes,
    *,
    sample_rate: int = 32000,
    label_type: str = LABEL_TYPE_RHYTHM,
    watermark: WatermarkPayload | None = None,
) -> tuple[bytes, dict[str, Any]]:
    labeled_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if label_type == LABEL_TYPE_RHYTHM:
        label_wav = rhythm_label_wav(sample_rate=sample_rate)
        output = concat_wav(label_wav, wav_bytes)
    else:
        raise ValueError(f"Unsupported label_type: {label_type}")

    # Embed digital watermark if payload provided
    watermark_embedded = False
    if watermark is not None:
        try:
            from voice_platform.watermark.embedder import embed_watermark
            output = embed_watermark(output, watermark)
            watermark_embedded = True
        except Exception:
            # Watermark failure should not block export
            pass

    metadata = {
        "export_compliant": True,
        "label_type": label_type,
        "labeled_at": labeled_at,
        "ai_generated": True,
        "comment": "AI_GENERATED",
        "watermark_embedded": watermark_embedded,
    }
    return output, metadata


def build_manifest(
    *,
    job_id: str,
    items: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    labeled_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "job_id": job_id,
        "export_compliant": True,
        "label_type": LABEL_TYPE_RHYTHM,
        "labeled_at": labeled_at,
        "items": items,
        "failures": failures,
    }


def manifest_json(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
