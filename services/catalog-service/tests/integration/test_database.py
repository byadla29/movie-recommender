"""Integration tests against the real Compose Postgres (docker compose up -d postgres).

Run:  RUN_INTEGRATION=1 uv run pytest tests/integration
with DATABASE_URL (env or .env) pointing at this service's own database.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from catalog_service.db import get_engine
from catalog_service.readiness import check_readiness, expected_migration_head
from catalog_service.settings import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)

OWN_DATABASE = "catalog_db"
OTHER_DATABASES = ["user_db", "reco_db", "postgres"]


def test_ready_after_migrating_to_head() -> None:
    settings = get_settings()
    command.upgrade(Config(str(settings.alembic_ini_path)), "head")

    result = check_readiness(get_engine(), expected_migration_head(settings.alembic_ini_path))

    assert result.ready, result.checks


def test_connected_to_own_database() -> None:
    assert make_url(get_settings().database_url.get_secret_value()).database == OWN_DATABASE


@pytest.mark.parametrize("other_db", OTHER_DATABASES)
def test_service_role_cannot_connect_to_other_databases(other_db: str) -> None:
    """Data ownership is enforced by Postgres itself, not just by convention."""
    own_url = make_url(get_settings().database_url.get_secret_value())
    engine = create_engine(own_url.set(database=other_db))

    with (
        pytest.raises(OperationalError, match="permission denied for database"),
        engine.connect(),
    ):
        pass
