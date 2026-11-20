"""Consent rules and request checks for consents/account endpoints. No database needed."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import user_service.models  # noqa: F401  (registers tables)
from user_service.db import Base
from user_service.domain.consents import CONSENT_PURPOSES, ConsentState, effective_consents

AsUser = Callable[[str], dict[str, str]]
URL = "/v1/me/consents/personalization_tracking"


def test_never_answered_means_not_granted() -> None:
    assert effective_consents({}) == [ConsentState("personalization_tracking", False, None)]


def test_stored_answer_is_used() -> None:
    when = datetime(2026, 11, 20, tzinfo=UTC)

    states = effective_consents({"personalization_tracking": (True, when)})

    assert states == [ConsentState("personalization_tracking", True, when)]


def test_database_check_allows_exactly_the_domain_purposes() -> None:
    check = next(
        c
        for c in Base.metadata.tables["user_consents"].constraints
        if c.name == "ck_user_consents_purpose_known"
    )
    sql = str(check.sqltext)  # type: ignore[attr-defined]

    assert all(f"'{p}'" in sql for p in CONSENT_PURPOSES)


@pytest.mark.parametrize(
    ("method", "url"),
    [("GET", "/v1/me/consents"), ("PUT", URL), ("DELETE", "/v1/me")],
)
def test_every_endpoint_requires_a_token(
    client: TestClient, as_user: AsUser, method: str, url: str
) -> None:
    response = client.request(method, url, json={"granted": True})

    assert response.status_code == 401


def test_unknown_purpose_is_422(client: TestClient, as_user: AsUser) -> None:
    response = client.put(
        "/v1/me/consents/marketing_emails", json={"granted": True}, headers=as_user("alice")
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["path", "purpose"]


@pytest.mark.parametrize("value", ["yes", "true", 1, None])
def test_consent_must_be_a_real_boolean(client: TestClient, as_user: AsUser, value: object) -> None:
    # Pydantic would normally accept "true"/"yes"/1 as True. For consent we refuse to guess.
    response = client.put(URL, json={"granted": value}, headers=as_user("alice"))

    assert response.status_code == 422


def test_missing_or_extra_fields_are_422(client: TestClient, as_user: AsUser) -> None:
    assert client.put(URL, json={}, headers=as_user("alice")).status_code == 422
    extra = {"granted": True, "user_sub": "bob"}
    assert client.put(URL, json=extra, headers=as_user("alice")).status_code == 422
