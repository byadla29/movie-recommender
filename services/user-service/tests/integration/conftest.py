"""Shared fixtures for tests against the real Compose Postgres.

The trick that keeps your local database clean: each test gets ONE connection with an
open transaction that is ROLLED BACK at the end. Everything the test (or the app, via
`db_session_override`) writes disappears afterwards, even committed-looking work, because
app "commits" only release SAVEPOINTs inside that outer transaction.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from user_service.db import get_engine, get_session
from user_service.settings import get_settings


@pytest.fixture
def migrated() -> None:
    command.upgrade(Config(str(get_settings().alembic_ini_path)), "head")


@pytest.fixture
def connection(migrated: None) -> Iterator[Connection]:
    with get_engine().connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()


def _savepoint_session(connection: Connection) -> Session:
    # create_savepoint: session.begin()/commit() become SAVEPOINT/RELEASE inside our
    # outer transaction, and an error only rolls back to the savepoint.
    return Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    with _savepoint_session(connection) as s:
        yield s


@pytest.fixture
def db_session_override(app: FastAPI, connection: Connection) -> None:
    """Make every API request in the test use the rolled-back connection."""

    def override() -> Iterator[Session]:
        with _savepoint_session(connection) as s:
            yield s

    app.dependency_overrides[get_session] = override
