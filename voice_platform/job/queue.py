from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

import redis

from voice_platform.config import get_settings


class JobQueue(ABC):
    @abstractmethod
    def enqueue_infer(self, job_id: UUID) -> int:
        """Push job id; return queue depth (approx)."""

    @abstractmethod
    def dequeue_infer(self, timeout_sec: int = 5) -> UUID | None:
        """Blocking pop for infer worker."""

    @abstractmethod
    def enqueue_train(self, job_id: UUID) -> int:
        """Push train job id."""

    @abstractmethod
    def dequeue_train(self, timeout_sec: int = 5) -> UUID | None:
        """Blocking pop for train worker."""

    @abstractmethod
    def enqueue_batch(self, job_id: UUID) -> int:
        """Push batch job id."""

    @abstractmethod
    def dequeue_batch(self, timeout_sec: int = 5) -> UUID | None:
        """Blocking pop for batch worker."""


class RedisJobQueue(JobQueue):
    def __init__(self, client: redis.Redis | None = None) -> None:
        settings = get_settings()
        self._client = client or redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self._infer_key = settings.infer_queue_key
        self._train_key = settings.train_queue_key
        self._batch_key = settings.batch_queue_key

    def enqueue_infer(self, job_id: UUID) -> int:
        self._client.rpush(self._infer_key, str(job_id))
        return int(self._client.llen(self._infer_key))

    def dequeue_infer(self, timeout_sec: int = 5) -> UUID | None:
        return self._dequeue(self._infer_key, timeout_sec)

    def enqueue_train(self, job_id: UUID) -> int:
        self._client.rpush(self._train_key, str(job_id))
        return int(self._client.llen(self._train_key))

    def dequeue_train(self, timeout_sec: int = 5) -> UUID | None:
        return self._dequeue(self._train_key, timeout_sec)

    def enqueue_batch(self, job_id: UUID) -> int:
        self._client.rpush(self._batch_key, str(job_id))
        return int(self._client.llen(self._batch_key))

    def dequeue_batch(self, timeout_sec: int = 5) -> UUID | None:
        return self._dequeue(self._batch_key, timeout_sec)

    def _dequeue(self, key: str, timeout_sec: int) -> UUID | None:
        try:
            item = self._client.blpop(key, timeout=timeout_sec)
        except Exception:
            return None
        if not item:
            return None
        return UUID(item[1])
