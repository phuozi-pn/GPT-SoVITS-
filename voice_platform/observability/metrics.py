"""
Prometheus 指标暴露模块。

提供最小 3 个指标（W3 架构评审要求）：
1. api_requests_total — 请求计数 (counter)
2. api_request_duration_seconds — 请求延迟 (histogram)
3. worker_jobs_total — Worker 处理 job 计数 (counter)

额外指标：
- worker_queue_depth — 各队列深度 (gauge)
- worker_job_duration_seconds — Worker job 处理延迟 (histogram)
"""

from __future__ import annotations

import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import ClassVar

from voice_platform.config import get_settings

logger = logging.getLogger(__name__)

# ── 内存指标存储（无需第三方库依赖）─────────────────────

_metrics_lock = threading.Lock()

# Counter: 请求总数
_api_requests_total: dict[str, int] = {}  # key: method+path

# Histogram: 请求延迟 (手动分桶)
_api_request_duration_buckets = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
_api_request_duration_sum: dict[str, float] = {}
_api_request_duration_count: dict[str, int] = {}
_api_request_duration_bucket_counts: dict[str, list[int]] = {}

# Counter: Worker job 处理
_worker_jobs_total: dict[str, int] = {}

# Gauge: Worker 队列深度
_worker_queue_depth: dict[str, int] = {}

# Histogram: Worker job 处理延迟
_worker_job_duration_sum: dict[str, float] = {}
_worker_job_duration_count: dict[str, int] = {}


def _ensure_keys(label: str) -> None:
    """确保指标字典中存在指定 label。"""
    if label not in _api_requests_total:
        _api_requests_total[label] = 0
    if label not in _api_request_duration_sum:
        _api_request_duration_sum[label] = 0.0
        _api_request_duration_count[label] = 0
        _api_request_duration_bucket_counts[label] = [0] * len(_api_request_duration_buckets)


# ── API 指标记录 ─────────────────────────────────────────

def record_api_request(method: str, path: str, duration_sec: float) -> None:
    """记录一次 API 请求。"""
    label = f"{method} {path}"
    with _metrics_lock:
        _ensure_keys(label)
        _api_requests_total[label] += 1
        _api_request_duration_sum[label] += duration_sec
        _api_request_duration_count[label] += 1
        for i, bound in enumerate(_api_request_duration_buckets):
            if duration_sec <= bound:
                _api_request_duration_bucket_counts[label][i] += 1


# ── Worker 指标记录 ──────────────────────────────────────

def record_worker_job(worker_name: str, duration_sec: float) -> None:
    """记录一次 Worker job 处理。"""
    with _metrics_lock:
        _worker_jobs_total[worker_name] = _worker_jobs_total.get(worker_name, 0) + 1
        _worker_job_duration_sum[worker_name] = _worker_job_duration_sum.get(worker_name, 0.0) + duration_sec
        _worker_job_duration_count[worker_name] = _worker_job_duration_count.get(worker_name, 0) + 1


def set_queue_depth(worker_name: str, depth: int) -> None:
    """更新 Worker 队列深度 gauge。"""
    with _metrics_lock:
        _worker_queue_depth[worker_name] = depth


# ── Prometheus 文本格式导出 ──────────────────────────────

def _histogram_quantile(
    buckets: list[float],
    counts: list[int],
    total: int,
    quantile: float,
) -> float:
    """手动计算 histogram quantile（近似）。"""
    if total == 0:
        return 0.0
    target = int(total * quantile)
    accumulated = 0
    for i, (bound, count) in enumerate(zip(buckets, counts)):
        accumulated += count
        if accumulated >= target:
            return bound
    return buckets[-1]


def generate_metrics_text() -> str:
    """生成 Prometheus text format 指标输出。"""
    lines: list[str] = []

    with _metrics_lock:
        # 1. api_requests_total
        lines.append("# HELP api_requests_total Total number of API requests.")
        lines.append("# TYPE api_requests_total counter")
        for label, count in sorted(_api_requests_total.items()):
            lines.append(f'api_requests_total{{endpoint="{label}"}} {count}')

        # 2. api_request_duration_seconds (summary)
        lines.append("# HELP api_request_duration_seconds API request duration in seconds.")
        lines.append("# TYPE api_request_duration_seconds summary")
        for label in sorted(_api_request_duration_sum.keys()):
            cnt = _api_request_duration_count.get(label, 0)
            sm = _api_request_duration_sum.get(label, 0.0)
            buckets = _api_request_duration_bucket_counts.get(label, [])
            lines.append(
                f'api_request_duration_seconds_count{{endpoint="{label}"}} {cnt}'
            )
            lines.append(
                f'api_request_duration_seconds_sum{{endpoint="{label}"}} {sm:.6f}'
            )
            p50 = _histogram_quantile(_api_request_duration_buckets, buckets, cnt, 0.5)
            p95 = _histogram_quantile(_api_request_duration_buckets, buckets, cnt, 0.95)
            lines.append(
                f'api_request_duration_seconds{{endpoint="{label}",quantile="0.5"}} {p50:.4f}'
            )
            lines.append(
                f'api_request_duration_seconds{{endpoint="{label}",quantile="0.95"}} {p95:.4f}'
            )

        # 3. worker_jobs_total
        lines.append("# HELP worker_jobs_total Total number of jobs processed by worker.")
        lines.append("# TYPE worker_jobs_total counter")
        for worker, count in sorted(_worker_jobs_total.items()):
            lines.append(f'worker_jobs_total{{worker="{worker}"}} {count}')

        # 4. worker_queue_depth (gauge)
        lines.append("# HELP worker_queue_depth Current queue depth per worker type.")
        lines.append("# TYPE worker_queue_depth gauge")
        for worker, depth in sorted(_worker_queue_depth.items()):
            lines.append(f'worker_queue_depth{{worker="{worker}"}} {depth}')

        # 5. worker_job_duration_seconds (summary)
        lines.append("# HELP worker_job_duration_seconds Worker job processing duration.")
        lines.append("# TYPE worker_job_duration_seconds summary")
        for worker in sorted(_worker_job_duration_sum.keys()):
            cnt = _worker_job_duration_count.get(worker, 0)
            sm = _worker_job_duration_sum.get(worker, 0.0)
            lines.append(
                f'worker_job_duration_seconds_count{{worker="{worker}"}} {cnt}'
            )
            lines.append(
                f'worker_job_duration_seconds_sum{{worker="{worker}"}} {sm:.6f}'
            )

    lines.append("")  # Prometheus 要求末尾空行
    return "\n".join(lines)


# ── HTTP Handler ─────────────────────────────────────────

class MetricsHandler(BaseHTTPRequestHandler):
    """Prometheus /metrics 端点处理器。"""

    def log_message(self, format, *args):
        """抑制访问日志。"""
        pass

    def do_GET(self):
        if self.path == "/metrics":
            body = generate_metrics_text()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()


# ── Metrics Server ───────────────────────────────────────

class MetricsServer:
    """独立 Prometheus metrics HTTP 服务器。"""

    def __init__(self, port: int = 9090) -> None:
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动后台 metrics 服务器。"""
        self._server = HTTPServer(("0.0.0.0", self._port), MetricsHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Prometheus metrics server listening on :%s", self._port)

    def stop(self) -> None:
        """停止 metrics 服务器。"""
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None


def start_metrics_server(port: int | None = None) -> MetricsServer:
    """便捷函数：启动 metrics 服务器。"""
    if port is None:
        port = int(__import__("os").environ.get("METRICS_PORT", "9090"))
    server = MetricsServer(port)
    server.start()
    return server
