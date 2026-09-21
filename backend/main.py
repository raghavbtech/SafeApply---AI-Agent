"""
SafeApply FastAPI Application Factory and Server Entrypoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.config import settings
from backend.errors import SafeApplyError, generic_exception_handler, safeapply_exception_handler
from backend.api.v1.health import router as health_router
from backend.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    print(f"[SafeApply API] Starting up in {settings.environment} mode.")
    print(f"[SafeApply API] Persistence backend: {settings.cosmos_database if settings.cosmos_endpoint else 'Local JSON'}")

    # Launch background mail poller & autonomous responder daemon
    if settings.mail_username and settings.mail_app_password:
        from background_sync import start_background_sync
        target_user = settings.safeapply_user_id or "niyamatkajal0104@gmail.com"
        start_background_sync(user_id=target_user)
        print(f"[SafeApply API] Background mail poller & auto-responder daemon started for {target_user}.")

    yield
    print("[SafeApply API] Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Autonomous Recruitment Defense & Job Hub API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate Limiting & CSRF Middleware
    from backend.security.rate_limiter import rate_limit_middleware
    from backend.security.csrf import csrf_protect_middleware

    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(csrf_protect_middleware)

    # Exception Handlers
    app.add_exception_handler(SafeApplyError, safeapply_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Mount Routes
    app.include_router(health_router)
    app.include_router(api_v1_router)

    # Serve React Frontend static assets & SPA index.html
    dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
    if os.path.exists(dist_dir):
        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_react_app(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("health/") or full_path in ("docs", "redoc", "openapi.json"):
                return {"error": "Not Found"}
            target = os.path.join(dist_dir, full_path)
            if full_path and os.path.exists(target) and os.path.isfile(target):
                return FileResponse(target)
            index_file = os.path.join(dist_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs"}
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "name": settings.app_name,
                "version": settings.app_version,
                "status": "online",
                "docs": "/docs",
                "notice": "React frontend not built yet. Run 'npm run build' in /frontend directory.",
            }

    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
