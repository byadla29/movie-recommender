"""Fast checks on the table definitions. No database needed."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import user_service.models  # noqa: F401  (registers tables)
from user_service.db import Base

TABLES = Base.metadata.tables


def test_expected_tables_exist() -> None:
    assert set(TABLES) == {
        "users",
        "user_preferences",
        "user_languages",
        "user_genres",
        "user_consents",
    }


def test_users_table_stores_no_personal_profile_fields() -> None:
    # Data minimisation: only the identity provider's opaque ID, never email or name.
    assert set(TABLES["users"].columns.keys()) == {"id", "user_sub", "created_at", "updated_at"}


def test_every_child_table_is_deleted_with_its_user() -> None:
    for name, table in TABLES.items():
        if name == "users":
            continue
        fks = [c for c in table.constraints if isinstance(c, ForeignKeyConstraint)]
        assert len(fks) == 1, name
        assert fks[0].referred_table.name == "users", name
        assert fks[0].ondelete == "CASCADE", name


def test_constraint_names_follow_the_naming_convention() -> None:
    languages = TABLES["user_languages"]
    names = {c.name for c in languages.constraints}

    assert {
        "pk_user_languages",
        "fk_user_languages_user_id_users",
        "uq_user_languages_user_id_rank",
        "ck_user_languages_rank_range",
        "ck_user_languages_language_code_format",
    } <= names
    assert any(isinstance(c, UniqueConstraint) for c in languages.constraints)
    assert any(isinstance(c, CheckConstraint) for c in languages.constraints)
