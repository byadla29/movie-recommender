"""Application factory.

Run with:  uvicorn reco_service.main:create_app --factory
A factory (instead of a module-level `app`) means importing this module has no side
effects, and tests can build an app with whatever settings they need.
"""

from fastapi import FastAPI

from reco_service.api.health import router as health_router
from reco_service.errors import register_exception_handlers
from reco_service.logging_config import configure_logging
from reco_service.request_context import RequestContextMiddleware
from reco_service.settings import get_settings

API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level)

    app = FastAPI(
        title="recommendation-service",
        version=API_VERSION,
        description="Events, candidate generation, ranking, explanations, evaluation.",
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    return app
