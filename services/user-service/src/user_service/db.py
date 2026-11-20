"""Database engine and ORM base class.

Phase 1 uses synchronous SQLAlchemy + psycopg 3. FastAPI runs plain `def` endpoints in a
thread pool, so sync DB calls don't block the event loop. That's simpler to learn than
async SQLAlchemy and fast enough here; we revisit only if measurements say so.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from user_service.settings import get_settings

# Predictable constraint names (e.g. "fk_user_languages_user_id_users") instead of names
# Postgres invents. Migrations can then refer to a constraint by a name we know in advance.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0_label)s",
}


class Base(DeclarativeBase):
    """All ORM models of this service inherit from this. Alembic reads Base.metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request, always closed afterwards.

    Routes that write open the transaction themselves (`with session.begin():`), so the
    COMMIT happens *before* the response is sent; if it fails, the client gets an error,
    never a 200 for data that wasn't saved. Tests override this to use a rolled-back
    transaction.
    """
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


@lru_cache
def get_engine() -> Engine:
    """Create the engine lazily, so importing the app never opens a connection."""
    settings = get_settings()
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,  # drop dead connections (e.g. after a Postgres restart)
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )
