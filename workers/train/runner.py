from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from voice_platform.job.schemas import TrainPayload
from voice_platform.quota.repository import QuotaRepository
from workers.base import BaseWorker
from workers.train.mode import build_train_adapter, resolve_train_mode

logger = logging.getLogger(__name__)


def _resolve_mock(use_mock: bool | None) -> bool:
    return resolve_train_mode(use_mock=use_mock) == "mock"


def _job_train_mode(record) -> str:
    if not record or not record.payload:
        return "mock"
    payload = TrainPayload.model_validate(record.payload)
    _, mode = build_train_adapter(hyperparams=payload.hyperparams)
    return mode


class TrainWorker(BaseWorker):
    """微调训练 Worker。"""

    def __init__(self, *, use_mock: bool | None = None) -> None:
        super().__init__()
        self._mock = use_mock
        self._adapter = None
        self._train_mode = "mock"

    def worker_name(self) -> str:
        return "Train"

    def queue_key(self) -> str:
        return "train"

    def use_mock(self) -> bool:
        return _resolve_mock(self._mock)

    def requires_gpu_for_job(self, record) -> bool | None:
        mode = _job_train_mode(record)
        if mode in ("mock", "quick", "cloud"):
            return False
        if mode == "engine":
            return True
        return None

    def prepare(self, session: Session) -> None:
        self._adapter, self._train_mode = build_train_adapter(use_mock=self._mock)

    def process(self, *, job_id: UUID, session: Session, record) -> dict:
        payload = TrainPayload.model_validate(record.payload)
        adapter, train_mode = build_train_adapter(
            use_mock=self._mock,
            hyperparams=payload.hyperparams,
        )
        logger.info(
            "train start job_id=%s trace_id=%s mode=%s",
            job_id,
            record.trace_id,
            train_mode,
        )
        result = adapter.run(
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
            "train succeeded job_id=%s mode=%s voice_version_id=%s",
            job_id,
            train_mode,
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
