from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
from domains.compliance.export import apply_compliance_label
from voice_platform.config import get_db_session, get_settings
from voice_platform.engine.paths import host_path_to_container, weights_path_for_api
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import InferPayload, JobStatus
from voice_platform.quota.repository import QuotaRepository
from voice_platform.storage.local import LocalStorage
from sqlalchemy.orm import Session

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
            "temperature": meta.get("temperature", 1.0),
            "speed_factor": meta.get("speed_factor", 1.0),
            "top_p": meta.get("top_p", 1.0),
        }
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
        duration_sec = min(2.0, max(0.5, len(ctx.payload.text) / 20.0))
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


def run_once(*, use_mock: bool = False) -> bool:
    queue = RedisJobQueue()
    job_id = queue.dequeue_infer(timeout_sec=5)
    if not job_id:
        return False

    session = get_db_session()
    jobs = JobRepository(session)
    storage = LocalStorage()
    adapter = MockEngineAdapter() if use_mock else EngineAdapter()

    record = jobs.get_job(job_id)
    if not record or record.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        session.close()
        return True

    jobs.mark_running(job_id)
    try:
        payload = InferPayload.model_validate(record.payload)
        voice = session.get(VoiceVersionRow, payload.voice_version_id)
        if not voice:
            raise RuntimeError(f"VoiceVersion not found: {payload.voice_version_id}")

        ctx = InferContext(
            job_id=job_id,
            owner_user_id=record.owner_user_id,
            payload=payload,
            voice=voice,
        )
        audio_bytes = adapter.synthesize(ctx)
        settings = get_settings()
        label_meta: dict = {}
        if settings.compliance_export_required:
            audio_bytes, label_meta = apply_compliance_label(
                audio_bytes,
                sample_rate=payload.sample_rate,
                label_type=settings.compliance_label_type,
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
            "chars_billed": len(payload.text),
            "export_compliant": bool(label_meta.get("export_compliant")),
            "label_type": label_meta.get("label_type"),
            "labeled_at": label_meta.get("labeled_at"),
        }
        jobs.mark_succeeded(job_id, result)
        QuotaRepository(session).record_chars(
            user_id=record.owner_user_id,
            job_id=job_id,
            char_count=len(payload.text),
        )
        logger.info("synthesize succeeded job_id=%s duration=%.2fs", job_id, duration)
    except Exception as exc:
        logger.exception("synthesize failed job_id=%s", job_id)
        jobs.mark_failed(job_id, str(exc))
    finally:
        session.close()
    return True


def run_loop(*, use_mock: bool = False, poll_interval_sec: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Infer worker started mock=%s", use_mock)
    while True:
        processed = run_once(use_mock=use_mock)
        if not processed:
            time.sleep(poll_interval_sec)


if __name__ == "__main__":
    from voice_platform.config import get_settings

    settings = get_settings()
    use_mock = settings.engine_mock or __import__("os").environ.get("ENGINE_MOCK", "false").lower() == "true"
    run_loop(use_mock=use_mock)
