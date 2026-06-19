"""
按模块注册 FastAPI 路由 — 单一注册入口，替代 main.py 平铺 include_router。
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from apps.api.architecture.modules import iter_route_specs

if TYPE_CHECKING:
    from fastapi import FastAPI


def _load_router(route_module: str):
    mod = importlib.import_module(f"apps.api.routes.{route_module}")
    router = getattr(mod, "router", None)
    if router is None:
        raise RuntimeError(f"apps.api.routes.{route_module} missing `router`")
    return router


def register_api_routers(app: FastAPI, *, prefix: str = "/api/v1") -> None:
    """按 architecture.modules 声明顺序挂载全部业务路由。"""
    for spec in iter_route_specs():
        app.include_router(
            _load_router(spec.route_module),
            prefix=prefix,
            tags=[spec.openapi_tag],
        )
