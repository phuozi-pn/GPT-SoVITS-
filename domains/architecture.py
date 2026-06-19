"""
领域层模块边界 — 与 apps/api/architecture 及前端 architecture 对齐。

规则：
  1. domains/<name>/service.py 为用例入口；禁止 routes 直接访问 repository
  2. 跨域编排经 ComplianceGateway 或显式应用服务，不绕过合规
  3. voice_platform/* 仅承载 ORM、仓储、引擎适配，不含业务流程
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DomainModuleId = Literal["platform", "produce", "voice", "social", "ops"]


@dataclass(frozen=True)
class DomainPackage:
    package: str
    module: DomainModuleId
    responsibility: str


DOMAIN_PACKAGES: tuple[DomainPackage, ...] = (
    # platform
    DomainPackage("auth", "platform", "身份与会话"),
    DomainPackage("jobs", "platform", "异步任务编排"),
    DomainPackage("quota", "platform", "用量配额"),
    DomainPackage("watermark", "platform", "数字水印检测"),
    DomainPackage("fingerprint", "platform", "音频指纹注册与搜索"),
    DomainPackage("emotion", "platform", "中文文本情感分析"),
    # produce
    DomainPackage("synthesis", "produce", "语音合成用例"),
    DomainPackage("script", "produce", "剧本解析与分段"),
    DomainPackage("projects", "produce", "短剧项目与 CSV"),
    DomainPackage("compliance", "produce", "敏感词、Gateway、合规导出"),
    # voice
    DomainPackage("voices", "voice", "音色档案与版本"),
    DomainPackage("training", "voice", "训练 Job"),
    DomainPackage("assets", "voice", "素材与质检"),
    DomainPackage("consents", "voice", "授权书"),
    DomainPackage("marketplace", "voice", "音色馆上架"),
    DomainPackage("licensing", "voice", "授权凭证"),
    DomainPackage("kyc", "voice", "实名认证"),
    DomainPackage("quality", "voice", "AB 评测"),
    DomainPackage("payment", "voice", "支付"),
    DomainPackage("settlement", "voice", "结算"),
    # social
    DomainPackage("social", "social", "关注、点赞"),
    DomainPackage("community", "social", "Feed 与私信"),
    # ops
    DomainPackage("developer", "ops", "API Key"),
)


def packages_for_module(module_id: DomainModuleId) -> list[str]:
    return [d.package for d in DOMAIN_PACKAGES if d.module == module_id]
