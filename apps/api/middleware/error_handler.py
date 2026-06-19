"""
全局异常处理器 — 统一 API 错误响应格式。

保证所有异常（包括未捕获的）都以一致的 JSON 格式返回:
    {
        "code": "ERROR_CODE",
        "message": "人类可读的描述",
        "details": {}  // 可选
    }

同时注册验证错误（422）的自定义格式。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _format_validation_errors(exc: RequestValidationError) -> dict[str, Any]:
    """将 Pydantic 验证错误列表转为结构化格式。"""
    issues: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = [p for p in err.get("loc", []) if p != "body"]
        issues.append({
            "field": ".".join(str(p) for p in loc) if loc else "(root)",
            "type": err.get("type", "value_error"),
            "message": err.get("msg", "验证失败"),
        })
    return {
        "code": "VALIDATION_ERROR",
        "message": "请求参数校验失败",
        "details": {"issues": issues},
    }


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI app 上注册全局异常处理器。"""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        """统一 HTTPException 响应格式。"""
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            # 已经是标准格式（如 raise_domain_http 产出的），直接返回
            return JSONResponse(
                status_code=exc.status_code,
                content=detail,
            )
        # 裸 HTTPException → 包装为标准格式
        message = str(detail) if detail else ""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": message or exc.__class__.__name__,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(request: Request, exc: RequestValidationError):
        """统一 Pydantic 验证错误格式。"""
        body = _format_validation_errors(exc)
        logger.warning(
            "Validation error path=%s issues=%d",
            request.url.path,
            len(body.get("details", {}).get("issues", [])),
        )
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        """兜底：未捕获异常 → 500。"""
        logger.exception(
            "Unhandled exception path=%s method=%s",
            request.url.path,
            request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后再试。",
            },
        )
