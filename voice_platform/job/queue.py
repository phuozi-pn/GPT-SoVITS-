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
        self._gpu_lock_key = settings.gpu_lock_key
        self._gpu_lock_ttl = settings.gpu_lock_ttl_sec

    # ── 标准入队 / 出队 ──────────────────────────────────

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

    # ── GPU 互斥锁 ──────────────────────────────────────

    def acquire_gpu_lock(self, worker_id: str) -> bool:
        """尝试获取 GPU 互斥锁。

        Returns:
            True 表示锁获取成功，False 表示 GPU 被其他 Worker 占用。
        """
        return self._client.set(
            self._gpu_lock_key,
            worker_id,
            nx=True,
            ex=self._gpu_lock_ttl,
        ) or False

    def release_gpu_lock(self) -> None:
        """释放 GPU 互斥锁。"""
        self._client.delete(self._gpu_lock_key)

    def gpu_lock_holder(self) -> str | None:
        """返回当前 GPU 锁持有者，无人持有时返回 None。"""
        return self._client.get(self._gpu_lock_key)

    # ── 队列深度查询 ────────────────────────────────────

    def queue_depth(self, key: str) -> int:
        """查询指定队列的深度。"""
        return int(self._client.llen(key) or 0)

    @property
    def redis(self):
        """暴露底层 Redis 客户端（用于 health_check ping）。"""
        return self._client

    # ── 内部方法 ─────────────────────────────────────────

    def _dequeue(self, key: str, timeout_sec: int) -> UUID | None:
        try:
            item = self._client.blpop(key, timeout=timeout_sec)
        except Exception:
            return None
        if not item:
            return None
        return UUID(item[1])
