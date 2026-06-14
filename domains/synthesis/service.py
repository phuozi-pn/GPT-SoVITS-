from __future__ import annotations

from uuid import UUID

from voice_platform.job.queue import JobQueue, RedisJobQueue
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import (
    InferPayload,
    JobRecord,
    JobStatus,
    JobSubmitResponse,
    JobType,
    SynthesisResponse,
)


class SynthesisService:
    def __init__(
        self,
        session,
        queue: JobQueue | None = None,
    ) -> None:
        self._jobs = JobRepository(session)
        self._queue = queue or RedisJobQueue()

    def submit(
        self, *, owner_user_id: UUID, payload: InferPayload, trace_id: str | None = None
    ) -> JobSubmitResponse:
        record = self._jobs.create_synthesize_job(
            owner_user_id=owner_user_id,
            payload=payload,
            trace_id=trace_id,
        )
        queue_position = self._queue.enqueue_infer(record.job_id)
        return JobSubmitResponse(
            job_id=record.job_id,
            job_type=JobType.SYNTHESIZE,
            status=JobStatus.QUEUED,
            queue_position=queue_position,
        )

    def get_job(self, job_id: UUID, owner_user_id: UUID) -> JobRecord | None:
        record = self._jobs.get_job(job_id)
        if not record or record.owner_user_id != owner_user_id:
            return None
        return record

    def to_response(self, record: JobRecord) -> SynthesisResponse:
        """Backward-compatible wrapper; prefer domains.jobs.service.record_to_response."""
        audio_url = duration_sec = chars_billed = None
        if record.result:
            audio_url = record.result.get("audio_url")
            duration_sec = record.result.get("duration_sec")
            chars_billed = record.result.get("chars_billed")
        return SynthesisResponse(
            job_id=record.job_id,
            status=record.status,
            audio_url=audio_url,
            duration_sec=duration_sec,
            chars_billed=chars_billed,
            queue_position=record.queue_position,
        )
