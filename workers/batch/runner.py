from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from domains.compliance.export import (
    COMPLIANCE_README,
    apply_compliance_label,
    build_manifest,
    manifest_json,
)
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from voice_platform.config import get_settings
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.repository import BatchLineRepository, JobRepository
from voice_platform.job.schemas import BatchLinePayload, BatchLineStatus, BatchPayload, InferPayload
from voice_platform.quota.repository import QuotaRepository
from voice_platform.storage.local import LocalStorage
from workers.base import BaseWorker
from workers.infer.runner import EngineAdapter, InferContext, MockEngineAdapter

logger = logging.getLogger(__name__)

_ROLE_SAFE = re.compile(r"[^\w\u4e00-\u9fff\-]+")
_gateway = ComplianceGateway()


def _safe_role(name: str) -> str:
    cleaned = _ROLE_SAFE.sub("_", name.strip())
    return cleaned or "role"


class BatchWorker(BaseWorker):
    """CSV 批量配音 + ZIP 打包 Worker。"""

    def __init__(self, *, use_mock: bool | None = None) -> None:
        super().__init__()
        self._mock = use_mock
        self._adapter: EngineAdapter | MockEngineAdapter | None = None
        self._storage: LocalStorage | None = None

    def worker_name(self) -> str:
        return "Batch"

    def queue_key(self) -> str:
        return "batch"

    def use_mock(self) -> bool:
        if self._mock is not None:
            return self._mock
        return get_settings().engine_mock

    def prepare(self, session: Session) -> None:
        self._adapter = MockEngineAdapter() if self.use_mock() else EngineAdapter()
        self._storage = LocalStorage()

    def process(self, *, job_id: UUID, session: Session, record) -> dict:
        assert self._adapter is not None
        assert self._storage is not None

        payload = BatchPayload.model_validate(record.payload)
        settings = get_settings()
        logger.info(
            "batch start job_id=%s trace_id=%s lines=%s",
            job_id,
            record.trace_id,
            len(payload.lines),
        )

        line_repo = BatchLineRepository(session)

        # 首次执行：创建行级记录（Worker 崩溃恢复时跳过已成功的行）
        existing_lines = line_repo.get_lines(job_id)
        if existing_lines.total == 0:
            line_repo.create_lines(
                job_id=job_id,
                lines=[
                    {
                        "index": line.index,
                        "role": line.role,
                        "text": line.text,
                        "voice_version_id": line.voice_version_id,
                    }
                    for line in payload.lines
                ],
            )

        lines = payload.lines
        succeeded: list[dict] = []
        failed: list[dict] = []

        for line in lines:
            # 跳过已成功的行（Worker 崩溃恢复）
            existing = line_repo.get_lines(job_id)
            already_done = {
                l.line_index
                for l in existing.lines
                if l.status == BatchLineStatus.SUCCEEDED
            }
            if line.index in already_done:
                logger.info("batch line already done job=%s idx=%s", job_id, line.index)
                succeeded.append(
                    {
                        "index": line.index,
                        "role": line.role,
                        "text": line.text,
                        "audio_url": next(
                            (l.audio_url for l in existing.lines if l.line_index == line.index),
                            "",
                        ),
                        "duration_sec": next(
                            (l.duration_sec or 0 for l in existing.lines if l.line_index == line.index),
                            0,
                        ),
                        "export_compliant": next(
                            (l.export_compliant for l in existing.lines if l.line_index == line.index),
                            False,
                        ),
                        "label_type": next(
                            (l.label_type for l in existing.lines if l.line_index == line.index),
                            None,
                        ),
                        "labeled_at": next(
                            (l.labeled_at.isoformat() if l.labeled_at else None for l in existing.lines if l.line_index == line.index),
                            None,
                        ),
                    }
                )
                continue

            line_repo.mark_line_running(job_id, line.index)

            try:
                audio_url, duration, label_meta = _synthesize_line(
                    adapter=self._adapter,
                    storage=self._storage,
                    owner_user_id=record.owner_user_id,
                    batch_job_id=job_id,
                    line=line,
                    session=session,
                    apply_label=settings.compliance_export_required,
                    label_type=settings.compliance_label_type,
                )
                export_compliant = label_meta.get("export_compliant", False)
                line_repo.mark_line_succeeded(
                    job_id,
                    line.index,
                    audio_url=audio_url,
                    duration_sec=duration,
                    export_compliant=export_compliant,
                    label_type=label_meta.get("label_type"),
                    labeled_at=label_meta.get("labeled_at"),
                )
                succeeded.append(
                    {
                        "index": line.index,
                        "role": line.role,
                        "text": line.text,
                        "audio_url": audio_url,
                        "duration_sec": duration,
                        "export_compliant": export_compliant,
                        "label_type": label_meta.get("label_type"),
                        "labeled_at": label_meta.get("labeled_at"),
                    }
                )
            except ComplianceError as exc:
                line_repo.mark_line_failed(
                    job_id, line.index, error_code=exc.code, error_message=exc.message
                )
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
                line_repo.mark_line_failed(
                    job_id, line.index, error_code="JOB_FAILED", error_message=str(exc)
                )
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
            zip_url = self._storage.public_url(
                _build_zip(
                    storage=self._storage,
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
            raise RuntimeError("All batch lines failed")

        logger.info("batch done job=%s ok=%s fail=%s", job_id, len(succeeded), len(failed))
        return result


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
        watermark = None
        try:
            from voice_platform.watermark.embedder import build_watermark_payload

            watermark = build_watermark_payload(
                user_id=str(owner_user_id),
                voice_id=str(line.voice_version_id),
                job_id=str(batch_job_id),
            )
        except Exception:
            pass
        audio_bytes, label_meta = apply_compliance_label(
            audio_bytes,
            label_type=label_type,
            watermark=watermark,
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
    BatchWorker(use_mock=use_mock).run_loop(poll_interval_sec=poll_interval_sec)


if __name__ == "__main__":
    import os

    from voice_platform.config import get_settings
    from voice_platform.observability.metrics import start_metrics_server
    from workers.health import start_health_server

    settings = get_settings()
    worker = BatchWorker()
    worker.use_mock = lambda: settings.engine_mock
    start_health_server(worker, port=int(os.environ.get("WORKER_HEALTH_PORT", "8083")))
    start_metrics_server(port=int(os.environ.get("METRICS_PORT", "9093")))
    worker.run_loop()
