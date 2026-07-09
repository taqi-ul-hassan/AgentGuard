"""FastAPI application entrypoint for Agent Guard."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_audits import router as audits_router
from app.api.routes_policies import router as policies_router
from app.api.routes_recommendations import router as recommendations_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import request_id_middleware
from app.storage.database import init_database


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown tasks."""
    configure_logging(settings.log_level)
    logger.info("agent_guard_startup", extra={"app_name": settings.app_name})
    init_database()
    yield
    logger.info("agent_guard_shutdown", extra={"app_name": settings.app_name})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Safety checkpoint API for clinical AI recommendations.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(request_id_middleware)

    register_exception_handlers(application)

    application.include_router(recommendations_router, prefix=settings.api_prefix)
    application.include_router(audits_router, prefix=settings.api_prefix)
    application.include_router(policies_router, prefix=settings.api_prefix)

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Return a minimal health status for containers and load balancers."""
        return {"status": "ok", "service": settings.app_name}

    return application


app = create_app()
