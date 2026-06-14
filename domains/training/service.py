from __future__ import annotations

from uuid import UUID

from voice_platform.job.queue import JobQueue, RedisJobQueue
from voice_platform.job.repository import JobRepository, VoiceRepository
from voice_platform.job.schemas import JobStatus, JobSubmitResponse, JobType, TrainPayload


class TrainingService:
    def __init__(self, session, queue: JobQueue | None = None) -> None:
        self._jobs = JobRepository(session)
        self._voices = VoiceRepository(session)
        self._queue = queue or RedisJobQueue()

    def submit(
        self,
        *,
        owner_user_id: UUID,
        payload: TrainPayload,
        trace_id: str | None = None,
    ) -> JobSubmitResponse:
        record = self._jobs.create_train_job(
            owner_user_id=owner_user_id,
            payload=payload,
            trace_id=trace_id,
        )
        queue_position = self._queue.enqueue_train(record.job_id)
        return JobSubmitResponse(
            job_id=record.job_id,
            job_type=JobType.TRAIN,
            status=JobStatus.QUEUED,
            queue_position=queue_position,
        )

    def resolve_train_inputs(
        self,
        *,
        voice_id: UUID,
        owner_user_id: UUID,
        voice_asset_id: UUID | None,
        consent_id: UUID | None,
        model_tag: str,
    ) -> tuple[TrainPayload | None, bool, bool, bool, bool]:
        owns = self._voices.user_owns_voice(voice_id, owner_user_id)

        asset = (
            self._voices.get_asset(voice_asset_id)
            if voice_asset_id
            else self._voices.default_asset_for_voice(voice_id)
        )
        consent = (
            self._voices.get_consent(consent_id)
            if consent_id
            else self._voices.default_consent_for_voice(voice_id)
        )

        consent_ok = consent is not None and consent.status == "approved"
        asset_locked = asset is not None and asset.locked
        asset_qc_passed = asset is not None and asset.qc_passed

        if not asset or not consent:
            return None, owns, consent_ok, asset_locked, asset_qc_passed

        hyperparams: dict = {}
        if asset.qc_result_json:
            ref_text = asset.qc_result_json.get("ref_text")
            if ref_text:
                hyperparams["ref_text"] = ref_text

        payload = TrainPayload(
            voice_id=voice_id,
            voice_asset_id=asset.id,
            consent_id=consent.id,
            model_tag=model_tag,
            asset_urls=[asset.storage_uri],
            hyperparams=hyperparams,
        )
        return payload, owns, consent_ok, asset_locked, asset_qc_passed
