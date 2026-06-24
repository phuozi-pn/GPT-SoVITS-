from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# ── 嵌套配置模型 ──────────────────────────────────────────

class DatabaseConfig(BaseSettings):
    """数据库连接配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://voice:voice_dev@localhost:5432/voice_platform"


class RedisConfig(BaseSettings):
    """Redis / 队列配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = "redis://localhost:6379/0"
    infer_queue_key: str = "jobs:infer"
    train_queue_key: str = "jobs:train"
    batch_queue_key: str = "jobs:batch"
    gpu_lock_key: str = "gpu:lock"
    gpu_lock_ttl_sec: int = 3600


class StorageConfig(BaseSettings):
    """文件存储配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    storage_root: str = "./data/storage"
    storage_public_base_url: str = "http://localhost:8001/files"


class EngineConfig(BaseSettings):
    """TTS 引擎配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    engine_tts_url: str = "http://127.0.0.1:9880"
    engine_mock: bool = False
    engine_train_root: str = ""
    engine_train_root_in_docker: str = "/workspace/GPT-SoVITS"
    engine_train_docker: str = ""
    engine_train_platform_mount: str = ""
    engine_train_sample_text: str = (
        "大家好，我是测试用户，今天我们来测试一下语音合成功能。"
    )
    train_mock: bool = True
    train_mode: str = "auto"
    train_use_asr: bool = True
    train_asr_language: str = "zh"
    # api_v2 zero-shot / quick_clone: reset to these before each /tts (overrides yaml `custom` finetunes)
    engine_default_gpt_weights: str = ""
    engine_default_sovits_weights: str = ""
    # Remote GPU fine-tune (AutoDL / cloud VM via SSH)
    cloud_train_enabled: bool = False
    cloud_train_ssh_host: str = ""
    cloud_train_ssh_port: int = 22
    cloud_train_ssh_user: str = "root"
    cloud_train_ssh_key_path: str = ""
    cloud_train_remote_engine_root: str = "~/GPT-SoVITS"
    cloud_train_remote_platform_root: str = "~/GPT"
    cloud_train_remote_work_dir: str = "/root/cloud_train_jobs"
    cloud_train_ssh_timeout_sec: int = 7200
    cloud_train_local_dataset_prep: bool = True
    train_dataset_llm_enrich: bool = True


class AuthConfig(BaseSettings):
    """认证与授权配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    jwt_secret: str = "dev-change-me-in-production-32bytes-min!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    sms_mock: bool = True
    sms_otp_ttl_sec: int = 300
    auth_otp_max_failures: int = 5
    auth_lock_ttl_sec: int = 900
    dev_otp_code: str | None = None
    dev_skip_auth: bool = True
    dev_user_id: str = "00000000-0000-0000-0000-000000000001"
    dev_admin_user_id: str = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


class QuotaConfig(BaseSettings):
    """配额配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    quota_monthly_char_limit: int = 20000
    quota_monthly_train_limit: int = 1
    quota_timezone: str = "Asia/Shanghai"


class ComplianceConfig(BaseSettings):
    """合规 / 内容审核配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    compliance_wordlist_path: str = ""
    compliance_label_type: str = "rhythm"
    compliance_export_required: bool = True
    fingerprint_auto_enroll: bool = True


class AssetConfig(BaseSettings):
    """素材 / 质量管理配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    asset_max_bytes: int = 500 * 1024 * 1024
    qc_min_duration_sec: float = 480.0
    qc_max_duration_sec: float = 3600.0
    qc_min_sample_rate: int = 16000
    qc_dev_relax_duration: bool = False
    qc_dev_min_duration_sec: float = 3.0
    consent_auto_approve: bool = True
    asr_enabled: bool = True
    asr_mock: bool = False
    asr_clip_sec: float = 9.0
    asr_language: str = "zh"
    asr_model: str = "base"
    asr_device: str = "cpu"
    asr_compute_type: str = "int8"
    asr_mock_text: str = "这是一段用于开发测试的自动识别参考文本。"


class QualityConfig(BaseSettings):
    """音质评测配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    quality_similarity_threshold: float = 0.90
    quality_mock: bool = True
    quality_eval_sentence: str = "你好，这是一次音色相似度测评试听。"
    quality_eval_sentence_count: int = 1


class KYCConfig(BaseSettings):
    """实名认证配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    kyc_required: bool = True
    kyc_mock: bool = True
    kyc_provider: str = "auto"
    kyc_saas_submit_url: str = ""
    kyc_saas_api_key: str = ""
    kyc_saas_webhook_secret: str = ""


class PaymentConfig(BaseSettings):
    """支付 / 结算配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    payment_provider: str = "mock"
    payment_webhook_secret: str = "dev-payment-webhook-secret-change-me"
    payment_checkout_async: bool = False
    payment_notify_base_url: str = ""
    wechat_pay_app_id: str = ""
    wechat_pay_mch_id: str = ""
    wechat_pay_serial: str = ""
    wechat_pay_private_key: str = ""
    wechat_pay_private_key_path: str = ""
    wechat_pay_api_base: str = "https://api.mch.weixin.qq.com"
    alipay_app_id: str = ""
    alipay_private_key: str = ""
    alipay_private_key_path: str = ""
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    settlement_platform_fee_bps: int = 1500
    settlement_min_payout_cents: int = 10000


class ScriptConfig(BaseSettings):
    """AI 剧本解析配置 (DeepSeek)。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    script_parse_llm_enabled: bool = False
    script_parse_llm_mock: bool = False
    script_parse_max_chars: int = 12000
    script_parse_timeout_sec: float = 60.0


class ObservabilityConfig(BaseSettings):
    """可观测性配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    log_json: bool = False
    platform_release_version: str = "dev"
    alert_webhook_url: str = ""
    alert_on_job_failure: bool = True
    alert_webhook_format: str = "feishu"  # feishu | generic


class WebConfig(BaseSettings):
    """Web / CORS 配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    web_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    catalog_auto_approve: bool = False
    catalog_demo_text: str = "方源，你给我出来！"
    marketplace_invite_required: bool = True
    marketplace_quality_gate: bool = True
    web_public_base_url: str = "http://127.0.0.1:5173"


# ── 聚合 Settings（向后兼容） ────────────────────────────

class Settings(BaseSettings):
    """聚合配置 — 保持原有 get_settings().xxx 访问方式不变。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic field validation
        # for dynamically attached sub-config objects.
        _set = object.__setattr__
        _set(self, "db", DatabaseConfig())
        _set(self, "redis", RedisConfig())
        _set(self, "storage", StorageConfig())
        _set(self, "engine", EngineConfig())
        _set(self, "auth", AuthConfig())
        _set(self, "quota", QuotaConfig())
        _set(self, "compliance", ComplianceConfig())
        _set(self, "asset", AssetConfig())
        _set(self, "quality", QualityConfig())
        _set(self, "kyc", KYCConfig())
        _set(self, "payment", PaymentConfig())
        _set(self, "script", ScriptConfig())
        _set(self, "observability", ObservabilityConfig())
        _set(self, "web", WebConfig())

    # ── 属性代理：保持 get_settings().database_url 等访问方式兼容 ──

    # Database
    @property
    def database_url(self) -> str:
        return self.db.database_url

    # Redis / Queue
    @property
    def redis_url(self) -> str:
        return self.redis.redis_url

    @property
    def infer_queue_key(self) -> str:
        return self.redis.infer_queue_key

    @property
    def train_queue_key(self) -> str:
        return self.redis.train_queue_key

    @property
    def batch_queue_key(self) -> str:
        return self.redis.batch_queue_key

    @property
    def gpu_lock_key(self) -> str:
        return self.redis.gpu_lock_key

    @property
    def gpu_lock_ttl_sec(self) -> int:
        return self.redis.gpu_lock_ttl_sec

    # Storage
    @property
    def storage_root(self) -> str:
        return self.storage.storage_root

    @property
    def storage_public_base_url(self) -> str:
        return self.storage.storage_public_base_url

    # Engine
    @property
    def engine_tts_url(self) -> str:
        return self.engine.engine_tts_url

    @property
    def engine_mock(self) -> bool:
        return self.engine.engine_mock

    @property
    def engine_train_root(self) -> str:
        return self.engine.engine_train_root

    @property
    def engine_train_root_in_docker(self) -> str:
        return self.engine.engine_train_root_in_docker

    @property
    def engine_train_docker(self) -> str:
        return self.engine.engine_train_docker

    @property
    def engine_train_platform_mount(self) -> str:
        return self.engine.engine_train_platform_mount

    @property
    def engine_train_sample_text(self) -> str:
        return self.engine.engine_train_sample_text

    @property
    def train_mock(self) -> bool:
        return self.engine.train_mock

    @property
    def train_mode(self) -> str:
        return self.engine.train_mode

    @property
    def train_use_asr(self) -> bool:
        return self.engine.train_use_asr

    @property
    def train_asr_language(self) -> str:
        return self.engine.train_asr_language

    @property
    def engine_default_gpt_weights(self) -> str:
        return self.engine.engine_default_gpt_weights

    @property
    def engine_default_sovits_weights(self) -> str:
        return self.engine.engine_default_sovits_weights

    @property
    def cloud_train_enabled(self) -> bool:
        return self.engine.cloud_train_enabled

    @property
    def cloud_train_ssh_host(self) -> str:
        return self.engine.cloud_train_ssh_host

    @property
    def cloud_train_ssh_port(self) -> int:
        return self.engine.cloud_train_ssh_port

    @property
    def cloud_train_ssh_user(self) -> str:
        return self.engine.cloud_train_ssh_user

    @property
    def cloud_train_ssh_key_path(self) -> str:
        return self.engine.cloud_train_ssh_key_path

    @property
    def cloud_train_remote_engine_root(self) -> str:
        return self.engine.cloud_train_remote_engine_root

    @property
    def cloud_train_remote_platform_root(self) -> str:
        return self.engine.cloud_train_remote_platform_root

    @property
    def cloud_train_remote_work_dir(self) -> str:
        return self.engine.cloud_train_remote_work_dir

    @property
    def cloud_train_ssh_timeout_sec(self) -> int:
        return self.engine.cloud_train_ssh_timeout_sec

    @property
    def cloud_train_local_dataset_prep(self) -> bool:
        return self.engine.cloud_train_local_dataset_prep

    @property
    def train_dataset_llm_enrich(self) -> bool:
        return self.engine.train_dataset_llm_enrich

    # Auth
    @property
    def jwt_secret(self) -> str:
        return self.auth.jwt_secret

    @property
    def jwt_algorithm(self) -> str:
        return self.auth.jwt_algorithm

    @property
    def jwt_expire_days(self) -> int:
        return self.auth.jwt_expire_days

    @property
    def sms_mock(self) -> bool:
        return self.auth.sms_mock

    @property
    def sms_otp_ttl_sec(self) -> int:
        return self.auth.sms_otp_ttl_sec

    @property
    def auth_otp_max_failures(self) -> int:
        return self.auth.auth_otp_max_failures

    @property
    def auth_lock_ttl_sec(self) -> int:
        return self.auth.auth_lock_ttl_sec

    @property
    def dev_otp_code(self) -> str | None:
        return self.auth.dev_otp_code

    @property
    def dev_skip_auth(self) -> bool:
        return self.auth.dev_skip_auth

    @property
    def dev_user_id(self) -> str:
        return self.auth.dev_user_id

    @property
    def dev_admin_user_id(self) -> str:
        return self.auth.dev_admin_user_id

    # Quota
    @property
    def quota_monthly_char_limit(self) -> int:
        return self.quota.quota_monthly_char_limit

    @property
    def quota_monthly_train_limit(self) -> int:
        return self.quota.quota_monthly_train_limit

    @property
    def quota_timezone(self) -> str:
        return self.quota.quota_timezone

    # Compliance
    @property
    def compliance_wordlist_path(self) -> str:
        return self.compliance.compliance_wordlist_path

    @property
    def compliance_label_type(self) -> str:
        return self.compliance.compliance_label_type

    @property
    def compliance_export_required(self) -> bool:
        return self.compliance.compliance_export_required

    @property
    def fingerprint_auto_enroll(self) -> bool:
        return self.compliance.fingerprint_auto_enroll

    # Asset
    @property
    def asset_max_bytes(self) -> int:
        return self.asset.asset_max_bytes

    @property
    def qc_min_duration_sec(self) -> float:
        return self.asset.qc_min_duration_sec

    @property
    def qc_max_duration_sec(self) -> float:
        return self.asset.qc_max_duration_sec

    @property
    def qc_min_sample_rate(self) -> int:
        return self.asset.qc_min_sample_rate

    @property
    def qc_dev_relax_duration(self) -> bool:
        return self.asset.qc_dev_relax_duration

    @property
    def qc_dev_min_duration_sec(self) -> float:
        return self.asset.qc_dev_min_duration_sec

    @property
    def consent_auto_approve(self) -> bool:
        return self.asset.consent_auto_approve

    @property
    def asset_asr_enabled(self) -> bool:
        return self.asset.asr_enabled

    @property
    def asset_asr_mock(self) -> bool:
        return self.asset.asr_mock

    @property
    def asset_asr_clip_sec(self) -> float:
        return self.asset.asr_clip_sec

    @property
    def asset_asr_language(self) -> str:
        return self.asset.asr_language

    @property
    def asset_asr_model(self) -> str:
        return self.asset.asr_model

    @property
    def asset_asr_device(self) -> str:
        return self.asset.asr_device

    @property
    def asset_asr_compute_type(self) -> str:
        return self.asset.asr_compute_type

    @property
    def asset_asr_mock_text(self) -> str:
        return self.asset.asr_mock_text

    # Quality
    @property
    def quality_similarity_threshold(self) -> float:
        return self.quality.quality_similarity_threshold

    @property
    def quality_mock(self) -> bool:
        return self.quality.quality_mock

    @property
    def quality_eval_sentence(self) -> str:
        return self.quality.quality_eval_sentence

    @property
    def quality_eval_sentence_count(self) -> int:
        return self.quality.quality_eval_sentence_count

    # KYC
    @property
    def kyc_required(self) -> bool:
        return self.kyc.kyc_required

    @property
    def kyc_mock(self) -> bool:
        return self.kyc.kyc_mock

    @property
    def kyc_provider(self) -> str:
        return self.kyc.kyc_provider

    @property
    def kyc_saas_submit_url(self) -> str:
        return self.kyc.kyc_saas_submit_url

    @property
    def kyc_saas_api_key(self) -> str:
        return self.kyc.kyc_saas_api_key

    @property
    def kyc_saas_webhook_secret(self) -> str:
        return self.kyc.kyc_saas_webhook_secret

    @property
    def kyc_saas_configured(self) -> bool:
        return bool(self.kyc_saas_submit_url.strip() and self.kyc_saas_api_key.strip())

    # Payment
    @property
    def payment_provider(self) -> str:
        return self.payment.payment_provider

    @property
    def payment_webhook_secret(self) -> str:
        return self.payment.payment_webhook_secret

    @property
    def payment_checkout_async(self) -> bool:
        return self.payment.payment_checkout_async

    @property
    def payment_notify_base_url(self) -> str:
        return self.payment.payment_notify_base_url

    @property
    def wechat_pay_app_id(self) -> str:
        return self.payment.wechat_pay_app_id

    @property
    def wechat_pay_mch_id(self) -> str:
        return self.payment.wechat_pay_mch_id

    @property
    def wechat_pay_serial(self) -> str:
        return self.payment.wechat_pay_serial

    @property
    def wechat_pay_private_key(self) -> str:
        return self.payment.wechat_pay_private_key

    @property
    def wechat_pay_private_key_path(self) -> str:
        return self.payment.wechat_pay_private_key_path

    @property
    def wechat_pay_api_base(self) -> str:
        return self.payment.wechat_pay_api_base

    @property
    def alipay_app_id(self) -> str:
        return self.payment.alipay_app_id

    @property
    def alipay_private_key(self) -> str:
        return self.payment.alipay_private_key

    @property
    def alipay_private_key_path(self) -> str:
        return self.payment.alipay_private_key_path

    @property
    def alipay_gateway(self) -> str:
        return self.payment.alipay_gateway

    @property
    def settlement_platform_fee_bps(self) -> int:
        return self.payment.settlement_platform_fee_bps

    @property
    def settlement_min_payout_cents(self) -> int:
        return self.payment.settlement_min_payout_cents

    # Script (DeepSeek)
    @property
    def deepseek_api_key(self) -> str:
        return self.script.deepseek_api_key

    @property
    def deepseek_base_url(self) -> str:
        return self.script.deepseek_base_url

    @property
    def deepseek_model(self) -> str:
        return self.script.deepseek_model

    @property
    def script_parse_llm_enabled(self) -> bool:
        return self.script.script_parse_llm_enabled

    @property
    def script_parse_llm_mock(self) -> bool:
        return self.script.script_parse_llm_mock

    @property
    def script_parse_max_chars(self) -> int:
        return self.script.script_parse_max_chars

    @property
    def script_parse_timeout_sec(self) -> float:
        return self.script.script_parse_timeout_sec

    # Observability
    @property
    def log_json(self) -> bool:
        return self.observability.log_json

    @property
    def platform_release_version(self) -> str:
        return self.observability.platform_release_version

    @property
    def alert_webhook_url(self) -> str:
        return self.observability.alert_webhook_url

    @property
    def alert_on_job_failure(self) -> bool:
        return self.observability.alert_on_job_failure

    @property
    def alert_webhook_format(self) -> str:
        return self.observability.alert_webhook_format

    # Web
    @property
    def web_cors_origins(self) -> str:
        return self.web.web_cors_origins

    @property
    def catalog_auto_approve(self) -> bool:
        return self.web.catalog_auto_approve

    @property
    def catalog_demo_text(self) -> str:
        return self.web.catalog_demo_text

    @property
    def marketplace_invite_required(self) -> bool:
        return self.web.marketplace_invite_required

    @property
    def marketplace_quality_gate(self) -> bool:
        return self.web.marketplace_quality_gate

    @property
    def web_public_base_url(self) -> str:
        return self.web.web_public_base_url.rstrip("/")


# ── 工具函数 ──────────────────────────────────────────────

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
