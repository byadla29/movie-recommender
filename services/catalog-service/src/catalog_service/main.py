"""Application factory.

Run with:  uvicorn catalog_service.main:create_app --factory
A factory (instead of a module-level `app`) means importing this module has no side
effects, and tests can build an app with whatever settings they need.
"""

from fastapi import FastAPI

from catalog_service.api.health import router as health_router
from catalog_service.errors import register_exception_handlers
from catalog_service.logging_config import configure_logging
from catalog_service.request_context import RequestContextMiddleware
from catalog_service.settings import get_settings

API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level)

    app = FastAPI(
        title="catalog-service",
        version=API_VERSION,
        description="Movie metadata, genres, languages, search and permitted-data imports.",
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    return app
