"""Preferences API checks that never reach the database: auth and input validation.

Both happen *before* any SQL runs, so these tests need no Postgres. Saving and reading
real data is covered in tests/integration/test_preferences_api.py.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

AsUser = Callable[[str], dict[str, str]]

VALID_BODY: dict[str, Any] = {
    "country_code": "IN",
    "region_code": "IN-AP",
    "languages": ["te", "en"],
    "genres": ["thriller"],
}


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_no_token_is_401(client: TestClient, as_user: AsUser, method: str) -> None:
    response = client.request(method, "/v1/me/preferences", json=VALID_BODY)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


def test_bad_token_is_401_even_with_a_bad_body(client: TestClient, as_user: AsUser) -> None:
    # Authentication runs first: strangers learn nothing about our validation rules.
    response = client.put(
        "/v1/me/preferences", json={"nonsense": True}, headers={"Authorization": "Bearer x"}
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("change", "bad_field"),
    [
        ({"languages": []}, "languages"),  # at least one language
        ({"languages": ["te"] * 11}, "languages"),  # at most 10
        ({"genres": ["action"] * 6}, "genres"),  # at most 5
        ({"country_code": "in"}, "country_code"),  # must be upper case
        ({"region_code": "Andhra"}, "region_code"),  # must look like IN-AP
        ({"languages": ["Telugu"]}, "languages"),  # code, not a name
        ({"user_sub": "someone_else"}, "user_sub"),  # can't choose whose data to write
    ],
)
def test_bad_shape_is_422(
    client: TestClient, as_user: AsUser, change: dict[str, Any], bad_field: str
) -> None:
    response = client.put(
        "/v1/me/preferences", json={**VALID_BODY, **change}, headers=as_user("alice")
    )

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "https://errors.movie-reco.local/validation"
    assert any(bad_field in error["loc"] for error in body["errors"])


def test_missing_languages_is_422(client: TestClient, as_user: AsUser) -> None:
    body = {k: v for k, v in VALID_BODY.items() if k != "languages"}

    response = client.put("/v1/me/preferences", json=body, headers=as_user("alice"))

    assert response.status_code == 422


def test_unknown_codes_are_422_with_exact_locations(client: TestClient, as_user: AsUser) -> None:
    response = client.put(
        "/v1/me/preferences",
        json={**VALID_BODY, "languages": ["te", "xx"], "genres": ["masala"]},
        headers=as_user("alice"),
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert [(e["loc"], e["type"]) for e in response.json()["errors"]] == [
        (["body", "languages", 1], "unknown_code"),
        (["body", "genres", 0], "unknown_code"),
    ]
