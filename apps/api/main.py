from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import swagger_ui_bundle
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apps.api.config import get_settings
from voice_platform.config import ensure_storage_root
from voice_platform.observability.logging_config import configure_logging

from apps.api.middleware.error_handler import register_exception_handlers
from apps.api.middleware.metrics import MetricsMiddleware
from apps.api.middleware.rate_limit import RateLimitMiddleware
from apps.api.middleware.trace import TraceMiddleware
from apps.api.openapi import apply_modular_openapi
from apps.api.router_registry import register_api_routers

_SWAGGER_UI_DIR = Path(swagger_ui_bundle.__path__[0]) / "vendor" / "swagger-ui-4.15.5"
_API_VERSION = "v1"  # 修改此处即可全局切换 API 版本前缀


def _run_migrations() -> None:
    """
    启动时执行数据库迁移。

    优先使用 Alembic（版本化迁移）。
    如果 alembic_version 表不存在（新库 / 旧版升级），
    则回退到直接执行 infra/docker/migrations/*.sql 文件。
    """
    repo_root = Path(__file__).resolve().parents[2]

    # 1. 尝试 Alembic 版本化迁移
    alembic_ini = repo_root / "infra" / "docker" / "alembic.ini"
    if alembic_ini.is_file():
        import logging
        logger = logging.getLogger(__name__)
        try:
            import subprocess
            import sys

            result = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                logger.info("Alembic migrations applied successfully.")
                return
            logger.warning("Alembic upgrade returned %s: %s", result.returncode, result.stderr[:300])
        except Exception as exc:
            logger.warning("Alembic migration skipped: %s", exc)

    # 2. 回退：按文件名顺序执行 SQL，每条仅运行一次（platform_sql_migrations 记账）
    migrations_dir = repo_root / "infra" / "docker" / "migrations"
    if not migrations_dir.is_dir():
        return
    import logging

    import psycopg

    logger = logging.getLogger(__name__)
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    migrations = sorted(migrations_dir.glob("*.sql"))

    def _migration_number(name: str) -> int:
        try:
            return int(name.split("_", 1)[0])
        except ValueError:
            return 9999

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS platform_sql_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("SELECT COUNT(*) FROM platform_sql_migrations")
            tracking_empty = (cur.fetchone() or (0,))[0] == 0
            cur.execute("SELECT to_regclass('public.users')")
            existing_db = cur.fetchone()[0] is not None
            if tracking_empty and existing_db:
                # 已有业务数据的库首次启用记账：视为 034 之前的迁移均已执行过
                for migration in migrations:
                    if _migration_number(migration.name) < 34:
                        cur.execute(
                            "INSERT INTO platform_sql_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
                            (migration.name,),
                        )
                logger.info(
                    "Bootstrapped platform_sql_migrations for existing DB (%d files before 034)",
                    sum(1 for m in migrations if _migration_number(m.name) < 34),
                )
        conn.commit()

    for migration in migrations:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM platform_sql_migrations WHERE filename = %s",
                    (migration.name,),
                )
                if cur.fetchone():
                    continue
                sql = migration.read_text(encoding="utf-8")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO platform_sql_migrations (filename) VALUES (%s)",
                    (migration.name,),
                )
                logger.info("Applied SQL migration: %s", migration.name)
            conn.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from voice_platform.observability.metrics import start_metrics_server

    ensure_storage_root()
    _run_migrations()
    _metrics = start_metrics_server()
    try:
        yield
    finally:
        _metrics.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(json_logs=settings.log_json)
    api_prefix = f"/api/{_API_VERSION}"

    app = FastAPI(
        title="Voice Platform API",
        version="0.1.0",
        openapi_url=f"{api_prefix}/openapi.json",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    # swagger-ui 4.x only accepts OpenAPI 3.0.x (FastAPI defaults to 3.1.0)
    app.openapi_version = "3.0.3"
    app.add_middleware(TraceMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(MetricsMiddleware)
    register_exception_handlers(app)
    cors_origins = [o.strip() for o in settings.web_cors_origins.split(",") if o.strip()]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_api_routers(app, prefix=api_prefix)
    apply_modular_openapi(app)

    if _SWAGGER_UI_DIR.is_dir():
        app.mount(
            "/static/swagger-ui",
            StaticFiles(directory=str(_SWAGGER_UI_DIR)),
            name="swagger-ui",
        )

    @app.get(f"{api_prefix}/docs", include_in_schema=False)
    def swagger_ui():
        return get_swagger_ui_html(
            openapi_url=f"{api_prefix}/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=f"{api_prefix}/docs/oauth2-redirect",
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
        )

    @app.get(f"{api_prefix}/docs/oauth2-redirect", include_in_schema=False)
    def swagger_ui_oauth_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    storage_root = Path(get_settings().storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(storage_root)), name="files")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "release": settings.platform_release_version,
        }

    web_dist = Path(__file__).resolve().parents[1] / "web" / "dist"
    if web_dist.is_dir():
        assets_dir = web_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="web-assets")

        @app.get("/")
        def web_index():
            return FileResponse(web_dist / "index.html")

        @app.get("/{full_path:path}")
        def web_spa(full_path: str):
            if full_path.startswith(("api/", "files/", "static/")) or full_path == "health":
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            candidate = web_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app


app = create_app()
