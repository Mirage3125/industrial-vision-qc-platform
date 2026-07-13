import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.anomaly import router as anomaly_router
from backend.app.api.classical_vision import router as classical_vision_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.detection import router as detection_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.files import router as files_router
from backend.app.api.health import router as health_router
from backend.app.api.inspection import router as inspection_router
from backend.app.api.models import router as models_router
from backend.app.api.reviews import router as reviews_router
from backend.app.core.config import get_settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import request_context_middleware

settings = get_settings()
configure_logging(settings.log_level, settings.log_file)
logger = logging.getLogger("fvql")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("application_started", extra={"request_id": "system"})
    yield
    logger.info("application_stopped", extra={"request_id": "system"})


def create_app() -> FastAPI:
    """Application factory used by production and tests."""

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.logger = logger
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(request_context_middleware)
    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(classical_vision_router, prefix=settings.api_prefix)
    application.include_router(detection_router, prefix=settings.api_prefix)
    application.include_router(anomaly_router, prefix=settings.api_prefix)
    application.include_router(inspection_router, prefix=settings.api_prefix)
    application.include_router(reviews_router, prefix=settings.api_prefix)
    application.include_router(feedback_router, prefix=settings.api_prefix)
    application.include_router(models_router, prefix=settings.api_prefix)
    application.include_router(dashboard_router, prefix=settings.api_prefix)
    application.include_router(files_router, prefix=settings.api_prefix)
    register_exception_handlers(application)
    return application


app = create_app()
