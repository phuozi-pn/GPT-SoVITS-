from __future__ import annotations

import logging
import time
from uuid import UUID

from voice_platform.config import get_db_session, get_settings
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import JobRepository, VoiceVersionRepository
from voice_platform.job.schemas import JobStatus, MODEL_TAG_V2PRO, TrainPayload
from voice_platform.quota.repository import QuotaRepository
from workers.train.engine_adapter import EngineTrainAdapter

logger = logging.getLogger(__name__)


class MockTrainAdapter:
    """Creates VoiceVersion with placeholder checkpoint (no GPU fine-tune)."""

    def run(self, *, payload: TrainPayload, owner_user_id: UUID, job_id: UUID) -> dict:
        session = get_db_session()
        try:
            versions = VoiceVersionRepository(session)
            row = versions.create_version(
                voice_id=payload.voice_id,
                owner_user_id=owner_user_id,
                model_tag=payload.model_tag,
                checkpoint_uri=f"local://checkpoints/{payload.voice_id}/mock-{job_id}.ckpt",
                ref_audio_uri=payload.asset_urls[0] if payload.asset_urls else None,
                metadata={
                    "train_job_id": str(job_id),
                    "mock": True,
                    "voice_asset_id": str(payload.voice_asset_id),
                    "consent_id": str(payload.consent_id),
                },
            )
            return {
                "voice_version_id": str(row.id),
                "checkpoint_uri": row.checkpoint_uri,
                "model_tag": row.model_tag or MODEL_TAG_V2PRO,
                "version": row.version,
            }
        finally:
            session.close()


def _use_mock() -> bool:
    settings = get_settings()
    import os

    if os.environ.get("TRAIN_MOCK", "").lower() in ("true", "1", "yes"):
        return True
    if os.environ.get("TRAIN_MOCK", "").lower() in ("false", "0", "no"):
        return False
    return settings.train_mock


def run_once(*, use_mock: bool | None = None) -> bool:
    queue = RedisJobQueue()
    job_id = queue.dequeue_train(timeout_sec=5)
    if not job_id:
        return False

    mock = _use_mock() if use_mock is None else use_mock
    session = get_db_session()
    jobs = JobRepository(session)
    adapter = MockTrainAdapter() if mock else EngineTrainAdapter()

    record = jobs.get_job(job_id)
    if not record or record.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        session.close()
        return True

    jobs.mark_running(job_id)
    try:
        payload = TrainPayload.model_validate(record.payload)
        result = adapter.run(payload=payload, owner_user_id=record.owner_user_id, job_id=job_id)
        jobs.mark_succeeded(job_id, result)
        QuotaRepository(session).record_training(user_id=record.owner_user_id, job_id=job_id)
        logger.info(
            "train succeeded job_id=%s mock=%s voice_version_id=%s",
            job_id,
            mock,
            result.get("voice_version_id"),
        )
    except Exception as exc:
        logger.exception("train failed job_id=%s", job_id)
        jobs.mark_failed(job_id, str(exc))
    finally:
        session.close()
    return True


def run_loop(*, use_mock: bool | None = None, poll_interval_sec: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    mock = _use_mock() if use_mock is None else use_mock
    logger.info("Train worker started mock=%s", mock)
    while True:
        processed = run_once(use_mock=mock)
        if not processed:
            time.sleep(poll_interval_sec)


if __name__ == "__main__":
    run_loop()
