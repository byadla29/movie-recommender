import os
from collections.abc import Callable, Iterator

import pytest

# Unit tests must never need a real database. Point settings at an address nothing listens
# on; integration tests (RUN_INTEGRATION=1) provide a real DATABASE_URL instead.
if os.environ.get("RUN_INTEGRATION") != "1":
    os.environ["DATABASE_URL"] = "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none"
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from user_service.auth import (
    AuthenticatedUser,
    InvalidTokenError,
    TokenVerifier,
    _verifier_from_settings,
    get_token_verifier,
)
from user_service.db import get_engine
from user_service.main import create_app
from user_service.settings import get_settings

_CACHED_FACTORIES = (get_settings, get_engine, _verifier_from_settings)


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    for factory in _CACHED_FACTORIES:
        factory.cache_clear()
    yield
    for factory in _CACHED_FACTORIES:
        factory.cache_clear()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


TEST_TOKEN_PREFIX = "test-token-for:"  # noqa: S105  (fake test value, not a credential)


class FakeVerifier(TokenVerifier):
    """Stand-in for real token checks (those are tested in test_auth.py).

    "test-token-for:alice" authenticates as sub "alice"; anything else is invalid.
    Lets API tests focus on what a user may do, not on cryptography.
    """

    def __init__(self) -> None:
        pass

    def verify(self, token: str) -> AuthenticatedUser:
        if not token.startswith(TEST_TOKEN_PREFIX):
            raise InvalidTokenError("not a test token")
        return AuthenticatedUser(sub=token.removeprefix(TEST_TOKEN_PREFIX))


AsUser = Callable[[str], dict[str, str]]


@pytest.fixture
def as_user(app: FastAPI) -> AsUser:
    """Switch the app to fake auth; `as_user("alice")` gives headers to call as alice."""
    app.dependency_overrides[get_token_verifier] = FakeVerifier
    return lambda sub: {"Authorization": f"Bearer {TEST_TOKEN_PREFIX}{sub}"}


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False so we can assert on the 500 problem+json response.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
