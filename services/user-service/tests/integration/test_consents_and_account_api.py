"""Consents and account deletion against the real Postgres (rolled-back transaction)."""

import os
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from user_service.models import User, UserConsent, UserGenre, UserLanguage, UserPreferences

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
    ),
    pytest.mark.usefixtures("db_session_override"),
]

AsUser = Callable[[str], dict[str, str]]
CONSENTS = "/v1/me/consents"
TRACKING = "/v1/me/consents/personalization_tracking"
PREFS = "/v1/me/preferences"
ALICE_PREFS: dict[str, Any] = {
    "country_code": "IN",
    "region_code": "IN-AP",
    "languages": ["te", "en"],
    "genres": ["thriller"],
}


def _user_count(session: Session, sub: str) -> int | None:
    return session.scalar(select(func.count()).where(User.user_sub == sub))


def _rows_for(session: Session, sub: str) -> dict[str, int | None]:
    """How many rows this user has in each table (via a subquery on users)."""
    user_id = select(User.id).where(User.user_sub == sub).scalar_subquery()
    return {
        model.__tablename__: session.scalar(
            select(func.count()).select_from(model).where(model.user_id == user_id)
        )
        for model in (UserPreferences, UserLanguage, UserGenre, UserConsent)
    }


# --- consents ------------------------------------------------------------------------------


def test_new_user_has_tracking_off_and_reading_creates_nothing(
    client: TestClient, as_user: AsUser, session: Session
) -> None:
    response = client.get(CONSENTS, headers=as_user("alice"))

    assert response.status_code == 200
    assert response.json() == {
        "consents": [{"purpose": "personalization_tracking", "granted": False, "updated_at": None}]
    }
    assert _user_count(session, "alice") == 0  # just looking leaves no trace


def test_grant_then_withdraw(client: TestClient, as_user: AsUser) -> None:
    granted = client.put(TRACKING, json={"granted": True}, headers=as_user("alice"))
    assert granted.status_code == 200
    assert granted.json()["granted"] is True
    assert granted.json()["updated_at"] is not None

    withdrawn = client.put(TRACKING, json={"granted": False}, headers=as_user("alice"))
    assert withdrawn.json()["granted"] is False

    [stored] = client.get(CONSENTS, headers=as_user("alice")).json()["consents"]
    assert stored["granted"] is False
    assert stored["updated_at"] is not None  # an explicit "no", not "never asked"


def test_consent_put_is_idempotent(client: TestClient, as_user: AsUser, session: Session) -> None:
    first = client.put(TRACKING, json={"granted": True}, headers=as_user("alice")).json()
    second = client.put(TRACKING, json={"granted": True}, headers=as_user("alice")).json()

    assert first == second
    assert _rows_for(session, "alice")["user_consents"] == 1


def test_consent_is_per_user(client: TestClient, as_user: AsUser) -> None:
    client.put(TRACKING, json={"granted": True}, headers=as_user("alice"))

    [bobs] = client.get(CONSENTS, headers=as_user("bob")).json()["consents"]
    assert bobs["granted"] is False


# --- account deletion -----------------------------------------------------------------------


def test_delete_me_removes_all_my_data_and_nobody_elses(
    client: TestClient, as_user: AsUser, session: Session
) -> None:
    for user in ("alice", "bob"):
        client.put(PREFS, json=ALICE_PREFS, headers=as_user(user))
        client.put(TRACKING, json={"granted": True}, headers=as_user(user))
    assert _rows_for(session, "alice") == {
        "user_preferences": 1,
        "user_languages": 2,
        "user_genres": 1,
        "user_consents": 1,
    }

    response = client.delete("/v1/me", headers=as_user("alice"))

    assert response.status_code == 204
    assert response.content == b""
    assert _user_count(session, "alice") == 0
    assert set(_rows_for(session, "alice").values()) == {0}
    # The API agrees: Alice is back to a brand-new, privacy-default state ...
    assert client.get(PREFS, headers=as_user("alice")).status_code == 404
    [consent] = client.get(CONSENTS, headers=as_user("alice")).json()["consents"]
    assert consent == {"purpose": "personalization_tracking", "granted": False, "updated_at": None}
    # ... and Bob is untouched.
    assert client.get(PREFS, headers=as_user("bob")).status_code == 200
    assert _rows_for(session, "bob")["user_consents"] == 1


def test_delete_is_idempotent(client: TestClient, as_user: AsUser) -> None:
    client.put(PREFS, json=ALICE_PREFS, headers=as_user("alice"))

    assert client.delete("/v1/me", headers=as_user("alice")).status_code == 204
    assert client.delete("/v1/me", headers=as_user("alice")).status_code == 204  # retry: fine


def test_delete_for_a_user_we_never_stored_is_204(client: TestClient, as_user: AsUser) -> None:
    assert client.delete("/v1/me", headers=as_user("never_seen")).status_code == 204
