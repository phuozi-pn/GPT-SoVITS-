"""
Worker 抽象基类 — 消除 infer / train / batch 的 run_loop / run_once 样板代码。

子类只需实现:
  - queue_key(): 返回 RedisJobQueue 的出队方法名
  - process(job_id, session, record): 执行业务逻辑
  - worker_name(): Worker 显示名（日志用）
  - use_mock(): 是否使用 Mock 适配器（默认读取配置）

可选覆写:
  - prepare(session): run_once 前置准备（如创建 adapter）
  - cleanup(session): run_once 后置清理
  - health_check(): 返回 Worker 健康状态 dict（默认检查 Redis/DB 连通性）
  - on_shutdown(): Worker 收到 SIGTERM/SIGINT 时的清理逻辑
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from voice_platform.config import get_db_session, get_settings
from voice_platform.job.queue import RedisJobQueue
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import JobStatus
from voice_platform.observability.metrics import record_worker_job, set_queue_depth

logger = logging.getLogger(__name__)

# ── 全局优雅关闭标志 ──────────────────────────────────────
_shutdown_requested = False


def _on_shutdown_signal(signum: int, frame: object) -> None:
    """SIGTERM / SIGINT 处理器 — 设置全局关闭标志。"""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating graceful shutdown...", sig_name)
    _shutdown_requested = True


def install_shutdown_handlers() -> None:
    """注册 SIGTERM / SIGINT 信号处理器。"""
    signal.signal(signal.SIGTERM, _on_shutdown_signal)
    signal.signal(signal.SIGINT, _on_shutdown_signal)


class BaseWorker(ABC):
    """Worker 基类 — 统一 run_loop / run_once 生命周期。"""

    def __init__(self) -> None:
        self._processed_count = 0
        self._last_health: dict | None = None
        self._started_at = time.time()
        self._gpu_lock_held = False
        self._worker_id = f"{self.worker_name()}-{os.getpid()}"

    # ── 子类必须覆写 ──────────────────────────────────────

    @abstractmethod
    def worker_name(self) -> str:
        """Worker 标识名，用于日志输出。"""

    @abstractmethod
    def queue_key(self) -> str:
        """
        返回 RedisJobQueue 对应的出队方法名。

        可选值: "infer" | "train" | "batch"
        """

    @abstractmethod
    def process(
        self,
        *,
        job_id: UUID,
        session: Session,
        record,
    ) -> dict | None:
        """
        执行核心业务逻辑。

        Args:
            job_id: Job ID
            session: DB Session（已注入，子类直接使用）
            record: JobRepository 查询结果行

        Returns:
            成功时返回 result dict → 传给 mark_succeeded
            返回 None 表示跳过（Worker 自行处理了 mark）

        Raises:
            Exception: 任何异常会被捕获并调用 mark_failed
        """

    # ── 可选覆写 ──────────────────────────────────────────

    def requires_gpu(self) -> bool:
        """
        是否在执行前需要获取 GPU 互斥锁。

        Infer 和 Train Worker 在非 Mock 模式下需要 GPU。
        默认：非 Mock 模式下需要。
        """
        return not self.use_mock()

    def requires_gpu_for_job(self, record) -> bool | None:
        """按任务覆写 GPU 需求；返回 None 时使用 requires_gpu()。"""
        return None

    def use_mock(self) -> bool:
        """是否启用 Mock 模式。默认从配置读取 engine_mock。"""
        return get_settings().engine_mock

    def prepare(self, session: Session) -> None:
        """run_once 前置准备（如初始化 adapter）。"""

    def cleanup(self, session: Session) -> None:
        """run_once 后置清理。"""

    def on_shutdown(self) -> None:
        """Worker 收到关闭信号时的清理钩子（子类可覆写）。"""

    def health_check(self) -> dict:
        """
        返回 Worker 健康状态 dict。

        默认检查 Redis 和 DB 连通性。子类可覆写添加自定义检查。
        """
        status = "healthy"
        checks: dict[str, bool | str] = {}

        # Redis 连通性
        try:
            queue = RedisJobQueue()
            queue.redis.ping()
            checks["redis"] = True
        except Exception as exc:
            checks["redis"] = str(exc)[:200]
            status = "unhealthy"

        # DB 连通性
        try:
            session = get_db_session()
            session.execute(text("SELECT 1"))
            session.close()
            checks["database"] = True
        except Exception as exc:
            checks["database"] = str(exc)[:200]
            status = "unhealthy"

        # GPU 锁状态
        try:
            queue = RedisJobQueue()
            holder = queue.gpu_lock_holder()
            checks["gpu_lock_holder"] = holder or "none"
        except Exception as exc:
            checks["gpu_lock_holder"] = f"error: {exc!s}"[:200]

        return {
            "worker": self.worker_name(),
            "status": status,
            "uptime_sec": round(time.time() - self._started_at, 1),
            "processed": self._processed_count,
            "mock": self.use_mock(),
            "checks": checks,
        }

    # ── 模板方法（无需覆写） ───────────────────────────────

    def _acquire_gpu_if_needed(self, queue: RedisJobQueue) -> bool:
        """如果 requires_gpu() 且当前未持有锁，则尝试获取 GPU 锁。"""
        if not self.requires_gpu():
            return True
        if self._gpu_lock_held:
            return True
        ok = queue.acquire_gpu_lock(self._worker_id)
        if ok:
            self._gpu_lock_held = True
            logger.info("GPU lock acquired by %s", self._worker_id)
        else:
            holder = queue.gpu_lock_holder()
            logger.debug("GPU lock held by %s, %s waiting...", holder, self._worker_id)
        return ok

    def _release_gpu_if_held(self, queue: RedisJobQueue) -> None:
        """如果当前持有 GPU 锁则释放。"""
        if self._gpu_lock_held:
            queue.release_gpu_lock()
            self._gpu_lock_held = False
            logger.info("GPU lock released by %s", self._worker_id)

    def _dequeue(self, queue: RedisJobQueue, timeout_sec: int = 5) -> UUID | None:
        """根据 queue_key 路由到对应出队方法。"""
        key = self.queue_key()
        mapping = {
            "infer": queue.dequeue_infer,
            "train": queue.dequeue_train,
            "batch": queue.dequeue_batch,
        }
        fn = mapping.get(key)
        if fn is None:
            raise ValueError(f"Unknown queue_key: {key}")
        return fn(timeout_sec)

    def run_once(self) -> bool:
        """单次轮询：出队 → 获取 GPU 锁(如需) → 校验状态 → mark_running → process → mark_succeeded/failed。"""
        queue = RedisJobQueue()
        job_id = self._dequeue(queue)
        if not job_id:
            # 上报队列深度（空轮询）
            try:
                key = self.queue_key()
                depth = queue.queue_depth(key)
                set_queue_depth(self.worker_name(), depth)
            except Exception:
                pass
            return False

        # GPU 互斥：按任务类型决定是否需要本地 GPU
        session_peek = get_db_session()
        record_peek = JobRepository(session_peek).get_job(job_id)
        session_peek.close()
        needs_gpu = self.requires_gpu_for_job(record_peek)
        if needs_gpu is None:
            needs_gpu = self.requires_gpu()
        if needs_gpu:
            if not self._acquire_gpu_if_needed(queue):
                # 锁被别人占着，把 job 放回队尾再等
                self._requeue(queue, job_id)
                time.sleep(1.0)
                return True

        start = time.perf_counter()
        session = get_db_session()
        jobs = JobRepository(session)

        record = jobs.get_job(job_id)
        if not record or record.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            self._release_gpu_if_held(queue)
            session.close()
            return True

        jobs.mark_running(job_id)
        try:
            self.prepare(session)
            result = self.process(job_id=job_id, session=session, record=record)
            if result is not None:
                jobs.mark_succeeded(job_id, result)
            logger.info("%s succeeded job_id=%s", self.worker_name(), job_id)
        except Exception as exc:
            logger.exception("%s failed job_id=%s", self.worker_name(), job_id)
            jobs.mark_failed(job_id, str(exc))
        finally:
            self.cleanup(session)
            self._release_gpu_if_held(queue)
            session.close()

        # 记录 job 处理指标
        duration = time.perf_counter() - start
        record_worker_job(self.worker_name(), duration)

        # 上报队列深度
        try:
            key = self.queue_key()
            depth = queue.queue_depth(key)
            set_queue_depth(self.worker_name(), depth)
        except Exception:
            pass

        self._processed_count += 1
        return True

    def _requeue(self, queue: RedisJobQueue, job_id: UUID) -> None:
        """将 job 重新放回队尾（GPU 锁未获取到时使用）。"""
        key = self.queue_key()
        mapping = {
            "infer": queue.enqueue_infer,
            "train": queue.enqueue_train,
            "batch": queue.enqueue_batch,
        }
        fn = mapping.get(key)
        if fn:
            fn(job_id)

    def run_loop(self, *, poll_interval_sec: float = 1.0) -> None:
        """主循环：初始化日志 → 循环 run_once，支持 SIGTERM/SIGINT 优雅关闭。"""
        from voice_platform.observability.logging_config import configure_logging

        global _shutdown_requested
        install_shutdown_handlers()

        settings = get_settings()
        configure_logging(json_logs=settings.log_json)
        logger.info(
            "%s worker started mock=%s pid=%s",
            self.worker_name(),
            self.use_mock(),
            os.getpid(),
        )

        try:
            while not _shutdown_requested:
                processed = self.run_once()
                if not processed:
                    time.sleep(poll_interval_sec)
        finally:
            logger.info(
                "%s worker shutting down (processed %s jobs in %.0fs)",
                self.worker_name(),
                self._processed_count,
                time.time() - self._started_at,
            )
            self.on_shutdown()
