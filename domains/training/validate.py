from __future__ import annotations

from uuid import UUID

from domains.cloud_train.service import user_can_cloud_train
from domains.voices.import_service import engine_train_root_ready
from voice_platform.cloud_train.config import is_cloud_train_configured
from voice_platform.config import get_settings


class TrainingServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def validate_train_backend(
    train_backend: str | None,
    *,
    session=None,
    user_id: UUID | None = None,
) -> None:
    backend = (train_backend or "").strip().lower()
    if not backend or backend == "auto":
        return
    if backend not in ("quick", "engine", "cloud"):
        raise TrainingServiceError("INVALID_TRAIN_BACKEND", f"不支持的训练方式：{backend}")

    settings = get_settings()
    if backend == "cloud":
        ok, _ = engine_train_root_ready()
        if not ok:
            raise TrainingServiceError(
                "ENGINE_ROOT_MISSING",
                "云端训练需要本机 ENGINE_TRAIN_ROOT 用于拉回权重后的合成",
                500,
            )
        if settings.train_mock:
            raise TrainingServiceError(
                "CLOUD_TRAIN_UNAVAILABLE",
                "请设置 TRAIN_MOCK=false 后重启平台",
            )
        if session is not None and user_id is not None:
            if not user_can_cloud_train(session, user_id):
                raise TrainingServiceError(
                    "CLOUD_GPU_NOT_CONNECTED",
                    "请先在 Studio 填写云端 GPU 的 SSH 信息并测试连接",
                )
        elif not is_cloud_train_configured(settings):
            raise TrainingServiceError(
                "CLOUD_GPU_NOT_CONNECTED",
                "请先在 Studio 填写云端 GPU 的 SSH 信息并测试连接",
            )
    if backend == "engine":
        ok, _ = engine_train_root_ready()
        if not ok:
            raise TrainingServiceError(
                "ENGINE_ROOT_MISSING",
                "本机 GPU 微调需要配置 ENGINE_TRAIN_ROOT",
                500,
            )


def cloud_train_issues() -> list[str]:
    settings = get_settings()
    issues: list[str] = []
    ok, _ = engine_train_root_ready()
    if not ok:
        issues.append("ENGINE_TRAIN_ROOT 未就绪")
    if settings.train_mock:
        issues.append("TRAIN_MOCK=true 会阻断云端训练")
    return issues
