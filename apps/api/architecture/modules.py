"""
后端 API 模块化注册表 — 与前端 architecture/modules.ts 对齐。

分层约定：
  routes/*.py   → HTTP 适配（校验、依赖注入、响应映射）
  domains/*     → 业务用例（事务边界、领域规则）
  voice_platform/* → 持久化、引擎、横切基础设施

模块划分：
  platform  鉴权、配额、Job、导出（横切）
  produce   合成、剧本解析、短剧项目
  voice     音色全生命周期 + 市场 + 支付结算
  social    动态流、私信、社区 Feed
  ops       运营、开放 API、开发者密钥
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ApiModuleId = Literal["platform", "produce", "voice", "social", "ops", "intelligence"]


@dataclass(frozen=True)
class ApiRouteSpec:
    """单一路由文件的元数据（不含 Router 实例，避免循环导入）。"""

    module: ApiModuleId
    route_module: str
    openapi_tag: str
    domain_packages: tuple[str, ...]
    summary: str


API_MODULES: tuple[tuple[ApiModuleId, str, tuple[ApiRouteSpec, ...]], ...] = (
    (
        "platform",
        "平台横切：鉴权、配额、异步任务、合规导出",
        (
            ApiRouteSpec("platform", "auth", "auth", ("auth",), "登录与会话"),
            ApiRouteSpec("platform", "usage", "usage", ("quota",), "配额与用量"),
            ApiRouteSpec("platform", "wallet", "wallet", ("wallet",), "用户 Token 钱包"),
            ApiRouteSpec("platform", "platform", "platform", (), "平台能力与配置"),
            ApiRouteSpec("platform", "jobs", "jobs", ("jobs",), "Job 状态查询"),
            ApiRouteSpec("platform", "exports", "exports", ("jobs", "compliance"), "合规导出下载"),
            ApiRouteSpec("platform", "compliance", "compliance", ("compliance",), "合成前文本合规预检"),
            ApiRouteSpec("platform", "watermark", "watermark", ("watermark",), "数字水印检测"),
            ApiRouteSpec("platform", "fingerprint", "fingerprint", ("fingerprint",), "音频指纹登记与检索"),
        ),
    ),
    (
        "produce",
        "制作：智能配音、剧本分段、短剧批量",
        (
            ApiRouteSpec("produce", "synthesis", "synthesis", ("synthesis", "compliance", "licensing"), "单条/多段合成"),
            ApiRouteSpec("produce", "script", "script", ("script",), "剧本 AI 分段"),
            ApiRouteSpec("produce", "projects", "projects", ("projects",), "短剧项目与 CSV 批量"),
            ApiRouteSpec("produce", "emotion", "emotion", ("emotion",), "自动情感识别"),
        ),
    ),
    (
        "voice",
        "音色：训练、资产、市场、授权、支付",
        (
            ApiRouteSpec("voice", "voices", "voices", ("voices", "training", "compliance", "kyc"), "音色与训练"),
            ApiRouteSpec("voice", "cloud_train", "cloud-gpu", ("cloud_train",), "用户云端 GPU 连接"),
            ApiRouteSpec("voice", "assets", "assets", ("assets",), "素材上传与质检"),
            ApiRouteSpec("voice", "consents", "consents", ("consents",), "授权书"),
            ApiRouteSpec("voice", "catalog", "catalog", ("marketplace",), "音色馆上架"),
            ApiRouteSpec("voice", "marketplace", "marketplace", ("marketplace",), "邀请制上架"),
            ApiRouteSpec("voice", "licensing", "licensing", ("licensing",), "授权凭证"),
            ApiRouteSpec("voice", "kyc", "kyc", ("kyc",), "实名认证"),
            ApiRouteSpec("voice", "quality", "quality", ("quality",), "相似度评测"),
            ApiRouteSpec("voice", "payments", "payments", ("payment",), "支付订单"),
            ApiRouteSpec("voice", "settlement", "settlement", ("settlement",), "卖家结算"),
            ApiRouteSpec("voice", "public_catalog", "public-catalog", ("marketplace",), "公开音色市场"),
        ),
    ),
    (
        "social",
        "社区：动态、私信",
        (
            ApiRouteSpec("social", "social", "social", ("social",), "关注与互动"),
            ApiRouteSpec("social", "community", "community", ("community",), "社区 Feed 与消息"),
        ),
    ),
    (
        "ops",
        "运营：审核、开放 API",
        (
            ApiRouteSpec("ops", "admin", "admin", ("jobs",), "运营台"),
            ApiRouteSpec("ops", "developer", "developer", ("developer",), "API Key 管理"),
            ApiRouteSpec("ops", "open_api", "open", ("developer", "synthesis", "compliance", "licensing"), "对外开放合成"),
        ),
    ),
    (
        "intelligence",
        "AI 智能：参数推荐、音色匹配、内容审核、情感增强",
        (
            ApiRouteSpec("intelligence", "intelligence", "intelligence", ("intelligence",), "AI 智能增强"),
        ),
    ),
)


def iter_route_specs() -> list[ApiRouteSpec]:
    out: list[ApiRouteSpec] = []
    for _, _, specs in API_MODULES:
        out.extend(specs)
    return out


def find_module_for_route_tag(tag: str) -> ApiModuleId | None:
    for spec in iter_route_specs():
        if spec.openapi_tag == tag:
            return spec.module
    return None
