from __future__ import annotations

from pathlib import Path
from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import JobRecord, JobResponse, JobStatus, JobType
from voice_platform.storage.local import LocalStorage


class JobService:
    """Domain service for admin job list & stats — wraps JobRepository."""

    def __init__(self, session) -> None:
        self._repo = JobRepository(session)
        self._session = session

    def list_recent(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        owner_user_id: UUID | None = None,
        limit: int = 50,
    ):
        return self._repo.list_recent(
            status=status,
            job_type=job_type,
            owner_user_id=owner_user_id,
            limit=limit,
        )

    def count_by_status(self, status: str) -> int:
        return self._repo.count_by_status(status)

    def count_failed_since(self, *, hours: int = 24) -> int:
        return self._repo.count_failed_since(hours=hours)

    def get_job_for_user(self, job_id: UUID, user_id: UUID) -> JobRecord | None:
        record = self._repo.get_job(job_id)
        if not record or record.owner_user_id != user_id:
            return None
        return record

    def resolve_export_download(
        self, *, job_id: UUID, user_id: UUID
    ) -> tuple[str, str, str]:
        """Resolve export download details for a completed job.

        Returns (absolute_path, filename, media_type).

        Raises JobExportError on any invalid state.
        """
        settings = get_settings()
        if not settings.compliance_export_required:
            raise JobExportError("LABEL_REQUIRED", "Compliant export is required", 403)

        record = self.get_job_for_user(job_id, user_id)
        if not record:
            raise JobExportError("JOB_NOT_FOUND", "Job not found", 404)
        if record.status != JobStatus.SUCCEEDED or not record.result:
            raise JobExportError("EXPORT_NOT_READY", "Job not completed successfully", 409)

        if record.job_type == JobType.SYNTHESIZE:
            if not record.result.get("export_compliant"):
                raise JobExportError("LABEL_REQUIRED", "Export is not compliance-labeled", 403)
            url = record.result.get("audio_url")
            filename = f"synthesis_{job_id}.wav"
        elif record.job_type == JobType.BATCH:
            if not record.result.get("zip_url"):
                raise JobExportError("EXPORT_NOT_FOUND", "Batch ZIP not available", 404)
            url = record.result["zip_url"]
            filename = f"batch_{job_id}.zip"
        else:
            raise JobExportError(
                "EXPORT_UNSUPPORTED", "Job type does not support export download", 400
            )

        rel = _rel_from_public_url(str(url))
        if not rel:
            raise JobExportError("EXPORT_PATH_INVALID", "Invalid export URL", 500)

        storage = LocalStorage()
        path = Path(storage.absolute_path(rel))
        if not path.is_file():
            raise JobExportError("EXPORT_FILE_MISSING", "Export file not found on disk", 404)

        media = "application/zip" if path.suffix == ".zip" else "audio/wav"
        return str(path), filename, media


class JobExportError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def get_job_for_user(session, job_id: UUID, user_id: UUID) -> JobRecord | None:
    """Deprecated: use JobService.get_job_for_user instead."""
    return JobService(session).get_job_for_user(job_id, user_id)


def _rel_from_public_url(url: str) -> str | None:
    marker = "/files/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1]


def record_to_response(record: JobRecord) -> JobResponse:
    resp = JobResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        trace_id=record.trace_id,
        owner_user_id=record.owner_user_id,
        queue_position=record.queue_position,
        error_message=record.error_message,
    )
    if record.result:
        if record.job_type == JobType.SYNTHESIZE:
            resp.audio_url = record.result.get("audio_url")
            resp.duration_sec = record.result.get("duration_sec")
            resp.chars_billed = record.result.get("chars_billed")
        elif record.job_type == JobType.TRAIN:
            vv = record.result.get("voice_version_id")
            resp.voice_version_id = UUID(vv) if vv else None
            resp.checkpoint_uri = record.result.get("checkpoint_uri")
            resp.model_tag = record.result.get("model_tag")
        elif record.job_type == JobType.BATCH:
            resp.line_count = record.result.get("line_count")
            resp.succeeded_count = record.result.get("succeeded_count")
            resp.failed_count = record.result.get("failed_count")
            resp.zip_url = record.result.get("zip_url")
    return resp
