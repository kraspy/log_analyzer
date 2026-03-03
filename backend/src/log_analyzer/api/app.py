"""FastAPI application factory.

Uses the Factory pattern: `create_app()` builds and configures the
FastAPI instance. This makes testing easier — you can create a fresh
app for each test without global state leaking between tests.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from log_analyzer.config import Settings
from log_analyzer.infrastructure.db.session import create_session_factory

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — runs on startup and shutdown.

    Startup: create DB session factory, store in app.state.
    Shutdown: close DB connections, cleanup resources.
    """
    settings: Settings = app.state.settings

    # Create session factory (connection pool)
    app.state.session_factory = create_session_factory(
        settings.database_url,
        echo=settings.debug,
    )

    log.info("app_starting", debug=settings.debug, ai_available=settings.ai_available)
    yield
    log.info("app_shutting_down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Application settings. If None, loaded from environment.

    Returns:
        Configured FastAPI instance.
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="LOG Analyzer API",
        description="Nginx log analysis service with AI-powered insights",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Store settings in app state for access in routes
    app.state.settings = settings

    # CORS — allow frontend origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",  # Vite dev server
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from log_analyzer.api.routes.ai import router as ai_router
    from log_analyzer.api.routes.export import router as export_router
    from log_analyzer.api.routes.preview import router as preview_router
    from log_analyzer.api.routes.reports import router as reports_router
    from log_analyzer.api.routes.statistics import router as stats_router
    from log_analyzer.api.routes.upload import router as upload_router

    app.include_router(upload_router)
    app.include_router(reports_router)
    app.include_router(stats_router)
    app.include_router(ai_router)
    app.include_router(export_router)
    app.include_router(preview_router)

    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        """Return application health status."""
        return {"status": "ok"}

    return app
