"""
API 请求 Metrics 中间件 — 记录每个请求的计数和延迟。
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from voice_platform.observability.metrics import record_api_request


class MetricsMiddleware(BaseHTTPMiddleware):
    """记录 API 请求计数和延迟到 Prometheus 指标。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start

        # 构建短路径标签（去参数，聚合同类请求）
        path = request.url.path
        method = request.method

        record_api_request(method, path, duration)

        return response
