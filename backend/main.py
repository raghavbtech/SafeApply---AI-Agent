"""
SafeApply FastAPI Application Factory and Server Entrypoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
