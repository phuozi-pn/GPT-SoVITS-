from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from domains.compliance.export import (
    COMPLIANCE_README,
    apply_compliance_label,
    build_manifest,
    manifest_json,
)
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from voice_platform.config import get_db_session, get_settings
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import BatchLinePayload, BatchPayload, InferPayload, JobStatus
from voice_platform.quota.repository import QuotaRepository
from voice_platform.storage.local import LocalStorage
from workers.infer.runner import EngineAdapter, InferContext, MockEngineAdapter

logger = logging.getLogger(__name__)

_ROLE_SAFE = re.compile(r"[^\w\u4e00-\u9fff\-]+")
_gateway = ComplianceGateway()


def _safe_role(name: str) -> str:
    cleaned = _ROLE_SAFE.sub("_", name.strip())
    return cleaned or "role"


def run_once(*, use_mock: bool = False) -> bool:
    queue = RedisJobQueue()
    job_id = queue.dequeue_batch(timeout_sec=5)
    if not job_id:
        return False

    session = get_db_session()
    jobs = JobRepository(session)
    storage = LocalStorage()
    adapter = MockEngineAdapter() if use_mock else EngineAdapter()
    settings = get_settings()

    record = jobs.get_job(job_id)
    if not record or record.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        session.close()
        return True

    jobs.mark_running(job_id)
    try:
        payload = BatchPayload.model_validate(record.payload)
        lines = payload.lines
        succeeded: list[dict] = []
        failed: list[dict] = []

        for line in lines:
            try:
                audio_url, duration, label_meta = _synthesize_line(
                    adapter=adapter,
                    storage=storage,
                    owner_user_id=record.owner_user_id,
                    batch_job_id=job_id,
                    line=line,
                    session=session,
                    apply_label=settings.compliance_export_required,
                    label_type=settings.compliance_label_type,
                )
                succeeded.append(
                    {
                        "index": line.index,
                        "role": line.role,
                        "text": line.text,
                        "audio_url": audio_url,
                        "duration_sec": duration,
                        "export_compliant": label_meta.get("export_compliant", False),
                        "label_type": label_meta.get("label_type"),
                        "labeled_at": label_meta.get("labeled_at"),
                    }
                )
            except ComplianceError as exc:
                failed.append(
                    {
                        "index": line.index,
                        "role": line.role,
                        "error_code": exc.code,
                        "error": exc.message,
                    }
                )
            except Exception as exc:
                logger.exception("batch line failed job=%s idx=%s", job_id, line.index)
                failed.append(
                    {
                        "index": line.index,
                        "role": line.role,
                        "error_code": "JOB_FAILED",
                        "error": str(exc),
                    }
                )

        zip_url = None
        if succeeded:
            zip_url = storage.public_url(
                _build_zip(
                    storage=storage,
                    user_id=record.owner_user_id,
                    job_id=job_id,
                    succeeded=succeeded,
                    failures=failed,
                )
            )
            char_total = sum(len(item["text"]) for item in succeeded)
            QuotaRepository(session).record_chars(
                user_id=record.owner_user_id,
                job_id=job_id,
                char_count=char_total,
            )

        result = {
            "line_count": len(lines),
            "succeeded_count": len(succeeded),
            "failed_count": len(failed),
            "items": succeeded,
            "failures": failed,
            "zip_url": zip_url,
            "export_compliant": bool(succeeded and settings.compliance_export_required),
        }
        if not succeeded:
            jobs.mark_failed(job_id, "All batch lines failed")
        else:
            jobs.mark_succeeded(job_id, result)
            logger.info("batch done job=%s ok=%s fail=%s", job_id, len(succeeded), len(failed))
    except Exception as exc:
        logger.exception("batch failed job_id=%s", job_id)
        jobs.mark_failed(job_id, str(exc))
    finally:
        session.close()
    return True


def _synthesize_line(
    *,
    adapter,
    storage: LocalStorage,
    owner_user_id: UUID,
    batch_job_id: UUID,
    line: BatchLinePayload,
    session,
    apply_label: bool,
    label_type: str,
) -> tuple[str, float, dict]:
    cleaned = _gateway.validate_batch_line_text(line.text)
    voice = session.get(VoiceVersionRow, line.voice_version_id)
    if not voice:
        raise RuntimeError(f"VoiceVersion not found: {line.voice_version_id}")

    ctx = InferContext(
        job_id=batch_job_id,
        owner_user_id=owner_user_id,
        payload=InferPayload(voice_version_id=line.voice_version_id, text=cleaned),
        voice=voice,
    )
    audio_bytes = adapter.synthesize(ctx)
    label_meta: dict = {}
    if apply_label:
        audio_bytes, label_meta = apply_compliance_label(
            audio_bytes,
            label_type=label_type,
        )
    role = _safe_role(line.role)
    rel = storage.save_bytes(
        user_id=owner_user_id,
        job_id=batch_job_id,
        data=audio_bytes,
        ext="wav",
        relative_name=f"batch/{batch_job_id}/{line.index:04d}_{role}.wav",
    )
    duration = LocalStorage.wav_duration_sec(storage.absolute_path(rel))
    return storage.public_url(rel), round(duration, 2), label_meta


def _build_zip(
    *,
    storage: LocalStorage,
    user_id: UUID,
    job_id: UUID,
    succeeded: list[dict],
    failures: list[dict],
) -> str:
    import io
    import zipfile

    manifest = build_manifest(
        job_id=str(job_id),
        items=succeeded,
        failures=failures,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("COMPLIANCE_README.txt", COMPLIANCE_README.encode("utf-8"))
        zf.writestr("manifest.json", manifest_json(manifest))
        for item in succeeded:
            url = item.get("audio_url") or ""
            rel_part = url.split("/files/", 1)[-1] if "/files/" in url else ""
            if not rel_part:
                continue
            src = Path(storage.absolute_path(rel_part))
            if src.is_file():
                role = _safe_role(str(item["role"]))
                arc = f"{role}/{item['index']:04d}_{role}.wav"
                zf.write(src, arcname=arc)
    return storage.save_bytes(
        user_id=user_id,
        job_id=job_id,
        data=buf.getvalue(),
        ext="zip",
        relative_name=f"batch/{job_id}/export_compliant.zip",
    )


def run_loop(*, use_mock: bool = False, poll_interval_sec: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Batch worker started mock=%s", use_mock)
    while True:
        processed = run_once(use_mock=use_mock)
        if not processed:
            import time

            time.sleep(poll_interval_sec)


if __name__ == "__main__":
    settings = get_settings()
    run_loop(use_mock=settings.engine_mock)
