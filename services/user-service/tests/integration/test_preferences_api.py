"""Preferences API end to end against the real Postgres (inside a rolled-back transaction).

The most important test here: one user can never see or change another user's data.
"""

import os
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from user_service.models import User, UserLanguage
from user_service.repositories import preferences as repo

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
    ),
    pytest.mark.usefixtures("db_session_override"),
]

AsUser = Callable[[str], dict[str, str]]
URL = "/v1/me/preferences"

ALICE_PREFS: dict[str, Any] = {
    "country_code": "IN",
    "region_code": "IN-AP",
    "languages": ["te", "en"],
    "genres": ["thriller", "drama"],
}
BOB_PREFS: dict[str, Any] = {
    "country_code": "GB",
    "languages": ["en"],
    "genres": ["comedy"],
}


def test_get_before_onboarding_is_404(client: TestClient, as_user: AsUser) -> None:
    response = client.get(URL, headers=as_user("alice"))

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_put_then_get_returns_what_was_saved(client: TestClient, as_user: AsUser) -> None:
    saved = client.put(URL, json=ALICE_PREFS, headers=as_user("alice"))
    fetched = client.get(URL, headers=as_user("alice"))

    assert saved.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json() == saved.json()
    body = fetched.json()
    assert body["country_code"] == "IN"
    assert body["region_code"] == "IN-AP"
    assert body["languages"] == [{"code": "te", "rank": 1}, {"code": "en", "rank": 2}]
    assert body["genres"] == ["drama", "thriller"]  # stored sorted
    assert body["onboarded_at"] and body["updated_at"]


def test_put_is_idempotent(client: TestClient, as_user: AsUser, session: Session) -> None:
    first = client.put(URL, json=ALICE_PREFS, headers=as_user("alice"))
    second = client.put(URL, json=ALICE_PREFS, headers=as_user("alice"))

    assert first.json() == second.json()
    # Same state, not doubled rows: still exactly one user row and two language rows.
    alice = select(User.id).where(User.user_sub == "alice").scalar_subquery()
    assert session.scalar(select(func.count()).where(User.user_sub == "alice")) == 1
    languages = select(func.count()).where(UserLanguage.user_id == alice)
    assert session.scalar(languages) == 2


def test_put_replaces_everything(client: TestClient, as_user: AsUser) -> None:
    first = client.put(URL, json=ALICE_PREFS, headers=as_user("alice")).json()

    changed = {"country_code": "IN", "languages": ["en", "te", "hi"], "genres": []}
    second = client.put(URL, json=changed, headers=as_user("alice")).json()

    # Swapping te/en ranks works (the unique (user_id, rank) rule doesn't get in the way).
    assert [lang["code"] for lang in second["languages"]] == ["en", "te", "hi"]
    assert second["region_code"] is None  # omitted = removed, because PUT replaces
    assert second["genres"] == []
    assert second["onboarded_at"] == first["onboarded_at"]  # first onboarding is kept


def test_rejected_put_changes_nothing(client: TestClient, as_user: AsUser) -> None:
    original = client.put(URL, json=ALICE_PREFS, headers=as_user("alice")).json()

    bad = client.put(URL, json={**ALICE_PREFS, "languages": ["xx"]}, headers=as_user("alice"))

    assert bad.status_code == 422
    assert client.get(URL, headers=as_user("alice")).json() == original


def test_failure_halfway_through_saving_rolls_everything_back(
    client: TestClient, as_user: AsUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = client.put(URL, json=ALICE_PREFS, headers=as_user("alice")).json()

    # Simulate a crash AFTER the old languages/genres were deleted and new ones inserted.
    def crash(*_args: object) -> None:
        raise RuntimeError("simulated crash mid-transaction")

    monkeypatch.setattr(repo, "get_preferences", crash)
    response = client.put(URL, json=BOB_PREFS, headers=as_user("alice"))
    monkeypatch.undo()

    assert response.status_code == 500
    # All-or-nothing: none of the half-finished changes were kept.
    assert client.get(URL, headers=as_user("alice")).json() == original


def test_users_only_ever_see_their_own_preferences(client: TestClient, as_user: AsUser) -> None:
    alice_saved = client.put(URL, json=ALICE_PREFS, headers=as_user("alice")).json()

    # Bob has saved nothing: he must NOT get Alice's data.
    assert client.get(URL, headers=as_user("bob")).status_code == 404

    bob_saved = client.put(URL, json=BOB_PREFS, headers=as_user("bob")).json()

    # Bob's PUT changed only Bob's data; each sees exactly their own.
    assert client.get(URL, headers=as_user("alice")).json() == alice_saved
    assert client.get(URL, headers=as_user("bob")).json() == bob_saved
    assert bob_saved["country_code"] == "GB"


def test_user_row_is_created_once_from_the_token_sub(
    client: TestClient, as_user: AsUser, session: Session
) -> None:
    client.put(URL, json=ALICE_PREFS, headers=as_user("user_2abcALICE"))

    count = session.scalar(select(func.count()).where(User.user_sub == "user_2abcALICE"))
    assert count == 1
