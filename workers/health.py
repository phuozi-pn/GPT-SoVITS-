"""
Worker 健康检查 HTTP 端点。

每个 Worker 进程在启动时通过后台线程暴露一个轻量 HTTP 端点，
供 Docker HEALTHCHECK / 监控系统查询 Worker 状态。

使用方式（在子类 run_loop 前调用）:
    from workers.health import start_health_server
    start_health_server(worker, port=8080)
"""

from __future__ import annotations

import http.server
import json
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workers.base import BaseWorker

logger = logging.getLogger(__name__)

_DEFAULT_PORT = 8080


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    """极简 HTTP 处理器 — 仅响应 GET /health。"""

    worker: BaseWorker | None = None  # 类属性，由 start_health_server 设置

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"code":"NOT_FOUND","message":"use GET /health"}\n')
            return

        try:
            if self.worker is None:
                raise RuntimeError("Worker not bound")
            data = self.worker.health_check()
            status_code = 200 if data.get("status") == "healthy" else 503
            body = json.dumps(data, ensure_ascii=False)
        except Exception as exc:
            status_code = 503
            body = json.dumps({
                "status": "unhealthy",
                "error": str(exc),
            }, ensure_ascii=False)

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, fmt: str, *args: object) -> None:
        """使用 logger 而非 stderr。"""
        logger.debug("health_server: %s", fmt % args)


def start_health_server(worker: BaseWorker, port: int = _DEFAULT_PORT) -> threading.Thread:
    """在后台线程启动健康检查 HTTP 服务器。

    Args:
        worker: Worker 实例
        port: 监听端口

    Returns:
        后台线程对象
    """
    _HealthHandler.worker = worker

    server = http.server.HTTPServer(("0.0.0.0", port), _HealthHandler)

    thread = threading.Thread(
        target=_serve_forever,
        args=(server, worker.worker_name(), port),
        daemon=True,
    )
    thread.start()
    logger.info("health server listening on 0.0.0.0:%s", port)
    return thread


def _serve_forever(server: http.server.HTTPServer, name: str, port: int) -> None:
    """包装 server.serve_forever 并捕获退出。"""
    try:
        server.serve_forever()
    except Exception:
        logger.exception("health server crashed for %s on port %s", name, port)
