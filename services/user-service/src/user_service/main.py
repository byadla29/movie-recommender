"""Application factory.

Run with:  uvicorn user_service.main:create_app --factory
A factory (instead of a module-level `app`) means importing this module has no side
effects, and tests can build an app with whatever settings they need.
"""

from fastapi import FastAPI

from user_service.api.health import router as health_router
from user_service.api.preferences import router as preferences_router
from user_service.errors import register_exception_handlers
from user_service.logging_config import configure_logging
from user_service.request_context import RequestContextMiddleware
from user_service.settings import get_settings

API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level)

    app = FastAPI(
        title="user-service",
        version=API_VERSION,
        description="Profiles, region/language/genre preferences, consents and watchlists.",
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(preferences_router)
    return app
