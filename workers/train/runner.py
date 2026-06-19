from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.config import get_db_session, get_settings
from voice_platform.job.repository import JobRepository, VoiceVersionRepository
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from voice_platform.quota.repository import QuotaRepository
from workers.base import BaseWorker
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


def _resolve_mock(use_mock: bool | None) -> bool:
    if use_mock is not None:
        return use_mock
    import os

    env_val = os.environ.get("TRAIN_MOCK", "").lower()
    if env_val in ("true", "1", "yes"):
        return True
    if env_val in ("false", "0", "no"):
        return False
    return get_settings().train_mock


class TrainWorker(BaseWorker):
    """微调训练 Worker。"""

    def __init__(self, *, use_mock: bool | None = None) -> None:
        super().__init__()
        self._mock = use_mock
        self._adapter: MockTrainAdapter | EngineTrainAdapter | None = None

    def worker_name(self) -> str:
        return "Train"

    def queue_key(self) -> str:
        return "train"

    def use_mock(self) -> bool:
        return _resolve_mock(self._mock)

    def prepare(self, session: Session) -> None:
        self._adapter = MockTrainAdapter() if self.use_mock() else EngineTrainAdapter()

    def process(self, *, job_id: UUID, session: Session, record) -> dict:
        assert self._adapter is not None
        payload = TrainPayload.model_validate(record.payload)
        logger.info(
            "train start job_id=%s trace_id=%s mock=%s",
            job_id,
            record.trace_id,
            self.use_mock(),
        )
        result = self._adapter.run(
            payload=payload,
            owner_user_id=record.owner_user_id,
            job_id=job_id,
        )
        QuotaRepository(session).record_training(
            user_id=record.owner_user_id,
            job_id=job_id,
        )
        vv_id = result.get("voice_version_id")
        if vv_id:
            from domains.quality.service import QualityService

            QualityService(session).evaluate_after_train(UUID(vv_id))
        logger.info(
            "train succeeded job_id=%s mock=%s voice_version_id=%s",
            job_id,
            self.use_mock(),
            result.get("voice_version_id"),
        )
        return result


def run_loop(*, use_mock: bool | None = None, poll_interval_sec: float = 1.0) -> None:
    TrainWorker(use_mock=use_mock).run_loop(poll_interval_sec=poll_interval_sec)


if __name__ == "__main__":
    import os

    from voice_platform.observability.metrics import start_metrics_server
    from workers.health import start_health_server

    worker = TrainWorker()
    start_health_server(worker, port=int(os.environ.get("WORKER_HEALTH_PORT", "8082")))
    start_metrics_server(port=int(os.environ.get("METRICS_PORT", "9092")))
    worker.run_loop()
