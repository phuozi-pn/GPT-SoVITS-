from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api.trace import ensure_trace_id, trace_context

logger = logging.getLogger(__name__)


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Trace-Id") or request.headers.get("X-Request-Id")
        trace_id = ensure_trace_id(incoming)
        started = time.perf_counter()
        with trace_context(trace_id):
            response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Trace-Id"] = trace_id
        if request.url.path not in ("/health", "/files"):
            logger.info(
                "%s %s -> %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response
