from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from domains.compliance.export import apply_compliance_label
from voice_platform.audio_util import concat_wav, pitch_shift_wav
from voice_platform.config import get_settings
from voice_platform.engine.paths import host_path_to_container, weights_path_for_api
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.repository import JobRepository, VoiceCatalogRepository
from voice_platform.job.schemas import InferPayload, InferSegment
from voice_platform.quota.repository import QuotaRepository
from voice_platform.storage.local import LocalStorage
from workers.base import BaseWorker

logger = logging.getLogger(__name__)


@dataclass
class InferContext:
    job_id: UUID
    owner_user_id: UUID
    payload: InferPayload
    voice: VoiceVersionRow


class EngineAdapter:
    """Calls upstream GPT-SoVITS api_v2 POST /tts."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or get_settings().engine_tts_url).rstrip("/")

    def synthesize(self, ctx: InferContext) -> bytes:
        meta = ctx.voice.metadata_json or {}
        ref_path = meta.get("engine_ref_audio_path") or ctx.voice.ref_audio_uri
        ref_text = ctx.voice.ref_text or meta.get("ref_text", "")
        if not ref_path:
            raise RuntimeError("VoiceVersion missing engine_ref_audio_path / ref_audio_uri")

        ref_path = host_path_to_container(ref_path)

        body = {
            "text": ctx.payload.text,
            "text_lang": meta.get("text_lang", "zh"),
            "ref_audio_path": ref_path,
            "prompt_text": ref_text,
            "prompt_lang": meta.get("prompt_lang", "zh"),
            "media_type": ctx.payload.format,
            "text_split_method": meta.get("text_split_method", "cut5"),
            "streaming_mode": False,
            "parallel_infer": False,
            "temperature": (
                ctx.payload.temperature
                if ctx.payload.temperature is not None
                else meta.get("temperature", 1.0)
            ),
            "speed_factor": (
                ctx.payload.speed_factor
                if ctx.payload.speed_factor is not None
                else meta.get("speed_factor", 1.0)
            ),
            "top_p": (
                ctx.payload.top_p if ctx.payload.top_p is not None else meta.get("top_p", 1.0)
            ),
        }
        # Pass emotion / emotion_strength if set (engine may use as auxiliary hint)
        if ctx.payload.emotion:
            body["emotion"] = ctx.payload.emotion
            body["emotion_strength"] = ctx.payload.emotion_strength
        with httpx.Client(timeout=300.0) as client:
            self._ensure_weights(client, meta)
            resp = client.post(f"{self._base_url}/tts", json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"Engine TTS failed ({resp.status_code}): {resp.text[:500]}")
            return resp.content

    def _ensure_weights(self, client: httpx.Client, meta: dict) -> None:
        if meta.get("mock"):
            return
        gpt_w, sovits_w = weights_path_for_api(meta)
        if not gpt_w or not sovits_w:
            logger.warning("VoiceVersion missing fine-tuned weights; using api_v2 defaults")
            return
        for endpoint, weights in (
            ("set_gpt_weights", gpt_w),
            ("set_sovits_weights", sovits_w),
        ):
            resp = client.get(
                f"{self._base_url}/{endpoint}",
                params={"weights_path": weights},
                timeout=300.0,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Engine {endpoint} failed ({resp.status_code}): {resp.text[:500]}"
                )
            logger.info("%s -> %s", endpoint, weights)


class MockEngineAdapter:
    """Returns minimal valid wav when GPU engine is unavailable."""

    def synthesize(self, ctx: InferContext) -> bytes:
        import struct
        import wave
        from io import BytesIO

        sample_rate = 32000
        text = ctx.payload.text or ""
        duration_sec = min(2.0, max(0.5, len(text) / 20.0))
        nframes = int(sample_rate * duration_sec)
        buf = BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(nframes):
                # quiet tone so duration metadata is non-zero
                val = int(800 * (1 if (i // 100) % 2 == 0 else -1))
                wf.writeframes(struct.pack("<h", val))
        return buf.getvalue()


def _segment_payload(base: InferPayload, seg: InferSegment) -> InferPayload:
    return InferPayload(
        voice_version_id=seg.voice_version_id,
        text=seg.text,
        format=base.format,
        sample_rate=base.sample_rate,
        catalog_id=base.catalog_id,
        skip_quota=base.skip_quota,
        temperature=seg.temperature if seg.temperature is not None else base.temperature,
        speed_factor=seg.speed_factor if seg.speed_factor is not None else base.speed_factor,
        top_p=seg.top_p if seg.top_p is not None else base.top_p,
        emotion=seg.emotion if seg.emotion is not None else base.emotion,
        emotion_strength=seg.emotion_strength if seg.emotion_strength != 0.5 else base.emotion_strength,
    )


def synthesize_payload(
    *,
    adapter: EngineAdapter | MockEngineAdapter,
    session: Session,
    job_id: UUID,
    owner_user_id: UUID,
    payload: InferPayload,
) -> bytes:
    if not payload.segments:
        voice = session.get(VoiceVersionRow, payload.voice_version_id)
        if not voice:
            raise RuntimeError(f"VoiceVersion not found: {payload.voice_version_id}")
        ctx = InferContext(
            job_id=job_id,
            owner_user_id=owner_user_id,
            payload=payload,
            voice=voice,
        )
        return adapter.synthesize(ctx)

    chunks: list[bytes] = []
    for i, seg in enumerate(payload.segments):
        voice = session.get(VoiceVersionRow, seg.voice_version_id)
        if not voice:
            raise RuntimeError(f"VoiceVersion not found: {seg.voice_version_id}")
        seg_payload = _segment_payload(payload, seg)
        ctx = InferContext(
            job_id=job_id,
            owner_user_id=owner_user_id,
            payload=seg_payload,
            voice=voice,
        )
        wav = adapter.synthesize(ctx)
        if abs(seg.pitch_factor - 1.0) >= 0.01:
            wav = pitch_shift_wav(wav, seg.pitch_factor)
        chunks.append(wav)
        # Insert silence pause between segments if requested
        if i < len(payload.segments) - 1 and seg.pause_duration > 0.0:
            from voice_platform.audio_util import silence_wav

            pause_wav = silence_wav(seg.pause_duration, sample_rate=payload.sample_rate)
            chunks.append(pause_wav)
    return concat_wav(chunks)


class InferWorker(BaseWorker):
    """TTS 合成 Worker。"""

    def __init__(self, *, use_mock: bool | None = None) -> None:
        super().__init__()
        self._mock = use_mock
        self._adapter: EngineAdapter | MockEngineAdapter | None = None

    def worker_name(self) -> str:
        return "Infer"

    def queue_key(self) -> str:
        return "infer"

    def use_mock(self) -> bool:
        if self._mock is not None:
            return self._mock
        return get_settings().engine_mock

    def prepare(self, session: Session) -> None:
        self._adapter = MockEngineAdapter() if self.use_mock() else EngineAdapter()

    def process(self, *, job_id: UUID, session: Session, record) -> dict:
        assert self._adapter is not None
        payload = InferPayload.model_validate(record.payload)
        logger.info(
            "synthesize start job_id=%s trace_id=%s",
            job_id,
            record.trace_id,
        )
        audio_bytes = synthesize_payload(
            adapter=self._adapter,
            session=session,
            job_id=job_id,
            owner_user_id=record.owner_user_id,
            payload=payload,
        )

        storage = LocalStorage()
        settings = get_settings()
        label_meta: dict = {}

        if settings.compliance_export_required:
            watermark = None
            try:
                from voice_platform.watermark.embedder import build_watermark_payload

                voice_id = str(payload.voice_version_id) if payload.voice_version_id else ""
                watermark = build_watermark_payload(
                    user_id=str(record.owner_user_id),
                    voice_id=voice_id,
                    job_id=str(job_id),
                )
            except Exception:
                pass
            audio_bytes, label_meta = apply_compliance_label(
                audio_bytes,
                sample_rate=payload.sample_rate,
                label_type=settings.compliance_label_type,
                watermark=watermark,
            )

        rel = storage.save_bytes(
            user_id=record.owner_user_id,
            job_id=job_id,
            data=audio_bytes,
            ext=payload.format,
        )
        abs_path = storage.absolute_path(rel)
        duration = LocalStorage.wav_duration_sec(abs_path)

        result = {
            "audio_url": storage.public_url(rel),
            "duration_sec": round(duration, 2),
            "chars_billed": payload.billed_char_count(),
            "export_compliant": bool(label_meta.get("export_compliant")),
            "label_type": label_meta.get("label_type"),
            "labeled_at": label_meta.get("labeled_at"),
            "watermark_embedded": bool(label_meta.get("watermark_embedded")),
        }

        if payload.catalog_id:
            VoiceCatalogRepository(session).set_demo_audio(
                payload.catalog_id,
                demo_audio_url=result["audio_url"],
            )

        if not payload.skip_quota:
            QuotaRepository(session).record_chars(
                user_id=record.owner_user_id,
                job_id=job_id,
                char_count=payload.billed_char_count(),
            )
            from domains.licensing.service import LicensingService

            LicensingService(session).record_synthesis_usage(
                user_id=record.owner_user_id,
                payload=payload,
            )
        else:
            logger.info("catalog demo job_id=%s skip_quota=1", job_id)

        logger.info("synthesize succeeded job_id=%s duration=%.2fs", job_id, duration)
        return result


def run_loop(*, use_mock: bool = False, poll_interval_sec: float = 1.0) -> None:
    InferWorker(use_mock=use_mock).run_loop(poll_interval_sec=poll_interval_sec)


if __name__ == "__main__":
    import os

    from voice_platform.config import get_settings
    from voice_platform.observability.metrics import start_metrics_server
    from workers.health import start_health_server

    settings = get_settings()
    use_mock = settings.engine_mock or os.environ.get("ENGINE_MOCK", "false").lower() == "true"
    worker = InferWorker()
    worker.use_mock = lambda: use_mock
    start_health_server(worker, port=int(os.environ.get("WORKER_HEALTH_PORT", "8081")))
    start_metrics_server(port=int(os.environ.get("METRICS_PORT", "9091")))
    worker.run_loop()
