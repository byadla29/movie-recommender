"""Schema tests against the real Compose Postgres.

Every test runs inside a transaction that is ROLLED BACK at the end, so these tests never
leave data behind or change the schema of your local database. Postgres supports this even
for CREATE/DROP TABLE ("transactional DDL").

Run:  RUN_INTEGRATION=1 uv run pytest tests/integration
"""

import os
import uuid
from collections.abc import Callable

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from user_service.db import Base
from user_service.models import User, UserConsent, UserGenre, UserLanguage, UserPreferences
from user_service.settings import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1 to run"
)

USER_TABLES = {"users", "user_preferences", "user_languages", "user_genres", "user_consents"}


def _alembic_config() -> Config:
    return Config(str(get_settings().alembic_ini_path))


# `connection` and `session` fixtures (rolled-back transaction) live in ./conftest.py.


def _user_with_everything(session: Session) -> User:
    user = User(user_sub=f"user_test_{uuid.uuid4().hex}")
    user.preferences = UserPreferences(country_code="IN", region_code="IN-AP")
    user.languages = [
        UserLanguage(language_code="te", rank=1),
        UserLanguage(language_code="en", rank=2),
    ]
    user.genres = [UserGenre(genre_slug="thriller"), UserGenre(genre_slug="drama")]
    user.consents = [UserConsent(purpose="personalization_tracking", granted=False)]
    session.add(user)
    session.flush()
    return user


def test_models_and_migrations_agree(connection: Connection) -> None:
    """If someone edits models.py but forgets a migration (or vice versa), this fails."""
    differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == []


def test_migration_downgrades_and_upgrades_cleanly(connection: Connection) -> None:
    config = _alembic_config()
    config.attributes["connection"] = connection  # run inside our rolled-back transaction

    command.downgrade(config, "0001")
    assert USER_TABLES.isdisjoint(inspect(connection).get_table_names())

    command.upgrade(config, "head")
    assert set(inspect(connection).get_table_names()) >= USER_TABLES


def test_database_fills_in_ids_and_timestamps(session: Session) -> None:
    user = _user_with_everything(session)
    session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.created_at.tzinfo is not None  # timestamptz, not a naive local time
    assert [lang.language_code for lang in user.languages] == ["te", "en"]  # ordered by rank


def test_deleting_a_user_deletes_all_their_rows(session: Session) -> None:
    user = _user_with_everything(session)
    user_id = user.id
    session.expunge_all()

    # A plain SQL DELETE: proves Postgres' ON DELETE CASCADE does it, not Python code.
    session.execute(delete(User).where(User.id == user_id))

    for model in (UserPreferences, UserLanguage, UserGenre, UserConsent):
        remaining = session.scalar(
            select(func.count()).select_from(model).where(model.user_id == user_id)
        )
        assert remaining == 0, model.__tablename__


@pytest.mark.parametrize(
    ("description", "build"),
    [
        ("lowercase country", lambda u: UserPreferences(user=u, country_code="in")),
        (
            "region from another country",
            lambda u: UserPreferences(user=u, country_code="IN", region_code="US-CA"),
        ),
        (
            "uppercase language code",
            lambda u: UserLanguage(user=u, language_code="TE", rank=1),
        ),
        ("rank above 10", lambda u: UserLanguage(user=u, language_code="te", rank=11)),
        ("rank 0", lambda u: UserLanguage(user=u, language_code="te", rank=0)),
        ("genre with capitals", lambda u: UserGenre(user=u, genre_slug="Sci-Fi")),
        (
            "unknown consent purpose",
            lambda u: UserConsent(user=u, purpose="marketing", granted=True),
        ),
    ],
)
def test_database_rejects_invalid_rows(
    session: Session, description: str, build: Callable[[User], Base]
) -> None:
    user = User(user_sub=f"user_test_{uuid.uuid4().hex}")
    session.add(user)
    session.flush()

    session.add(build(user))
    with pytest.raises(IntegrityError, match="violates check constraint"):
        session.flush()


def test_two_languages_cannot_share_a_rank(session: Session) -> None:
    user = User(user_sub=f"user_test_{uuid.uuid4().hex}")
    user.languages = [
        UserLanguage(language_code="te", rank=1),
        UserLanguage(language_code="en", rank=1),
    ]
    session.add(user)

    with pytest.raises(IntegrityError, match="uq_user_languages_user_id_rank"):
        session.flush()


def test_user_sub_is_unique(session: Session) -> None:
    session.add(User(user_sub="user_duplicate"))
    session.flush()
    session.add(User(user_sub="user_duplicate"))

    with pytest.raises(IntegrityError, match="uq_users_user_sub"):
        session.flush()
