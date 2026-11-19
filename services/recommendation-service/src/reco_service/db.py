"""Database engine and ORM base class.

Phase 1 uses synchronous SQLAlchemy + psycopg 3. FastAPI runs plain `def` endpoints in a
thread pool, so sync DB calls don't block the event loop. That's simpler to learn than
async SQLAlchemy and fast enough here; we revisit only if measurements say so.
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase

from reco_service.settings import get_settings


class Base(DeclarativeBase):
    """All ORM models of this service inherit from this. Alembic reads Base.metadata."""


@lru_cache
def get_engine() -> Engine:
    """Create the engine lazily, so importing the app never opens a connection."""
    settings = get_settings()
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,  # drop dead connections (e.g. after a Postgres restart)
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )
