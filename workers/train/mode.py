"""Train adapter selection (mock / quick clone / engine / cloud fine-tune)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from voice_platform.cloud_train.config import is_cloud_train_configured
from voice_platform.config import get_settings
from workers.train.cloud_adapter import CloudTrainAdapter
from workers.train.engine_adapter import EngineTrainAdapter
from workers.train.mock_adapter import MockTrainAdapter
from workers.train.quick_clone_adapter import QuickCloneTrainAdapter


def _requested_backend(hyperparams: dict[str, Any] | None) -> str:
    if not hyperparams:
        return ""
    return str(hyperparams.get("train_backend") or "").strip().lower()


def resolve_train_mode(
    *,
    use_mock: bool | None = None,
    train_backend: str | None = None,
) -> str:
    import os

    backend = (train_backend or "").strip().lower()

    # Studio 显式 train_backend=cloud 已在 API 层校验用户凭证，此处不再要求全局 CLOUD_TRAIN_*。
    if backend == "cloud":
        return "cloud"

    if use_mock is True:
        return "mock"
    if use_mock is False:
        explicit = (os.environ.get("TRAIN_MODE") or get_settings().train_mode or "").strip().lower()
        if explicit in ("mock", "quick", "engine", "cloud"):
            if explicit == "cloud" and not is_cloud_train_configured(get_settings()):
                pass
            else:
                return explicit
        root = (get_settings().engine_train_root or "").strip()
        if root and Path(root).is_dir():
            return "engine"
        return "quick"

    env_mock = os.environ.get("TRAIN_MOCK", "").lower()
    if env_mock in ("true", "1", "yes"):
        return "mock"
    if env_mock in ("false", "0", "no"):
        pass
    elif get_settings().train_mock:
        return "mock"

    if backend == "quick":
        return "quick"
    if backend == "engine":
        root = (get_settings().engine_train_root or "").strip()
        if root and Path(root).is_dir():
            return "engine"
        return "quick"

    mode = (os.environ.get("TRAIN_MODE") or get_settings().train_mode or "auto").strip().lower()
    if mode == "cloud":
        if is_cloud_train_configured(get_settings()):
            return "cloud"
    elif mode in ("mock", "quick", "engine"):
        return mode

    root = (get_settings().engine_train_root or "").strip()
    if root and Path(root).is_dir():
        return "engine"
    return "quick"


def build_train_adapter(*, use_mock: bool | None = None, hyperparams: dict[str, Any] | None = None):
    backend = _requested_backend(hyperparams)
    mode = resolve_train_mode(use_mock=use_mock, train_backend=backend or None)
    if mode == "mock":
        return MockTrainAdapter(), mode
    if mode == "cloud":
        return CloudTrainAdapter(), mode
    if mode == "quick":
        return QuickCloneTrainAdapter(), mode
    return EngineTrainAdapter(), mode


def train_mode_description(mode: str) -> str:
    if mode == "mock":
        return "占位训练（测试用，合成仍为 Mock 蜂鸣）"
    if mode == "quick":
        return "快速克隆：使用你的干声作为参考，经真实引擎 zero-shot 合成"
    if mode == "cloud":
        return "云端完整微调：上传干声 → 远端 GPU 切分/对齐/训练 → 权重拉回本机"
    return "GPU 微调：完整 GPT-SoVITS v2Pro 训练（需 ENGINE_TRAIN_ROOT + Docker GPU）"
