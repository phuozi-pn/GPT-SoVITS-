"""OpenAPI 文档按业务模块注入 tag 描述。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.api.architecture.modules import API_MODULES, iter_route_specs

if TYPE_CHECKING:
    from fastapi import FastAPI


def apply_modular_openapi(app: FastAPI) -> None:
    """为每个 OpenAPI tag 附加模块归属与能力说明。"""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )

        module_labels = {mid: label for mid, label, _ in API_MODULES}
        tag_meta: dict[str, dict[str, str]] = {}
        for spec in iter_route_specs():
            tag_meta[spec.openapi_tag] = {
                "name": spec.openapi_tag,
                "description": f"**[{module_labels[spec.module]} / {spec.module}]** {spec.summary}",
            }

        schema["tags"] = list(tag_meta.values())
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
