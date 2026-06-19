"""API 层模块化架构注册表。"""

from apps.api.architecture.modules import API_MODULES, ApiModuleId, find_module_for_route_tag

__all__ = ["API_MODULES", "ApiModuleId", "find_module_for_route_tag"]
