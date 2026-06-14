from __future__ import annotations

from uuid import UUID

from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import JobRecord, JobResponse, JobStatus, JobType


def get_job_for_user(session, job_id: UUID, user_id: UUID) -> JobRecord | None:
    record = JobRepository(session).get_job(job_id)
    if not record or record.owner_user_id != user_id:
        return None
    return record


def record_to_response(record: JobRecord) -> JobResponse:
    resp = JobResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
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
