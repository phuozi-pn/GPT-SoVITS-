from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from voice_platform.config import ensure_storage_root, get_settings

from apps.api.routes import assets, auth, consents, jobs, projects, synthesis, usage, voices


def _run_migrations() -> None:
    migrations_dir = Path(__file__).resolve().parents[2] / "infra" / "docker" / "migrations"
    if not migrations_dir.is_dir():
        return
    import psycopg

    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    for migration in sorted(migrations_dir.glob("*.sql")):
        sql = migration.read_text(encoding="utf-8")
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_storage_root()
    _run_migrations()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Voice Platform API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        lifespan=lifespan,
    )
    cors_origins = [o.strip() for o in settings.web_cors_origins.split(",") if o.strip()]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
    app.include_router(synthesis.router, prefix="/api/v1", tags=["synthesis"])
    app.include_router(voices.router, prefix="/api/v1", tags=["voices"])
    app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
    app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
    app.include_router(consents.router, prefix="/api/v1", tags=["consents"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])

    storage_root = Path(get_settings().storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(storage_root)), name="files")

    @app.get("/health")
    def health():
        return {"status": "ok"}

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
            if full_path.startswith("api/") or full_path.startswith("files/") or full_path == "health":
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            candidate = web_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app


app = create_app()
