import os
from collections.abc import Iterator

import pytest

# Unit tests must never need a real database. Point settings at an address nothing listens
# on; integration tests (RUN_INTEGRATION=1) provide a real DATABASE_URL instead.
if os.environ.get("RUN_INTEGRATION") != "1":
    os.environ["DATABASE_URL"] = "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none"
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from user_service.db import get_engine
from user_service.main import create_app
from user_service.settings import get_settings


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False so we can assert on the 500 problem+json response.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
