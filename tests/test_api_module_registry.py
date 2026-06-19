"""API 模块化注册表一致性测试。"""

from __future__ import annotations

import importlib

import pytest

from apps.api.architecture.modules import iter_route_specs


@pytest.mark.parametrize("spec", iter_route_specs(), ids=lambda s: s.route_module)
def test_route_module_exports_router(spec):
    mod = importlib.import_module(f"apps.api.routes.{spec.route_module}")
    assert hasattr(mod, "router"), f"{spec.route_module} must define `router`"


def test_all_expected_routes_registered():
    names = {s.route_module for s in iter_route_specs()}
    expected = {
        "auth",
        "usage",
        "jobs",
        "exports",
        "watermark",
        "fingerprint",
        "synthesis",
        "script",
        "projects",
        "emotion",
        "voices",
        "assets",
        "consents",
        "catalog",
        "licensing",
        "kyc",
        "quality",
        "payments",
        "settlement",
        "public_catalog",
        "social",
        "community",
        "admin",
        "developer",
        "open_api",
        "intelligence",
    }
    assert names == expected
