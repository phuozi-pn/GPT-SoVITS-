from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://voice:voice_dev@localhost:5432/voice_platform"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./data/storage"
    storage_public_base_url: str = "http://localhost:8001/files"
    engine_tts_url: str = "http://127.0.0.1:9880"
    engine_mock: bool = False
    dev_skip_auth: bool = True
    dev_user_id: str = "00000000-0000-0000-0000-000000000001"
    jwt_secret: str = "dev-change-me-in-production-32bytes-min!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    sms_mock: bool = True
    sms_otp_ttl_sec: int = 300
    auth_otp_max_failures: int = 5
    auth_lock_ttl_sec: int = 900
    dev_otp_code: str | None = None
    quota_monthly_char_limit: int = 20000
    quota_monthly_train_limit: int = 1
    quota_timezone: str = "Asia/Shanghai"
    train_mock: bool = True
    engine_train_root: str = ""
    engine_train_root_in_docker: str = "/workspace/GPT-SoVITS"
    engine_train_docker: str = ""
    engine_train_platform_mount: str = ""
    engine_train_sample_text: str = (
        "大家好，我是测试用户，今天我们来测试一下语音合成功能。"
    )
    infer_queue_key: str = "jobs:infer"
    train_queue_key: str = "jobs:train"
    batch_queue_key: str = "jobs:batch"
    gpu_lock_key: str = "gpu:lock"
    gpu_lock_ttl_sec: int = 3600
    consent_auto_approve: bool = True
    asset_max_bytes: int = 500 * 1024 * 1024
    qc_min_duration_sec: float = 480.0
    qc_max_duration_sec: float = 900.0
    qc_min_sample_rate: int = 16000
    qc_dev_relax_duration: bool = False
    qc_dev_min_duration_sec: float = 3.0
    web_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    train_use_asr: bool = True
    train_asr_language: str = "zh"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db_session() -> Session:
    return SessionLocal()


def ensure_storage_root() -> str:
    root = get_settings().storage_root
    os.makedirs(root, exist_ok=True)
    return root
