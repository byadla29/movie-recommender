"""ORM models: the Python view of user-service's tables in `user_db`.

The migration in `migrations/versions/0002_profile_and_preferences.py` is what actually creates
these tables; an integration test checks that models and migrations never drift apart.

What lives here (and what doesn't):
* `users` stores only the identity provider's `sub` (an opaque ID). No email, no name:
  we don't need them for recommendations, so we don't keep them (data minimisation).
* The database checks the *format* of codes ("te", "IN-AP"). Whether a code is in the
  allowed vocabulary (`contracts/vocab/`) is checked by the application (step 2.4),
  because the vocabulary can grow without a migration.
* Every child table points at `users.id` with ON DELETE CASCADE: deleting a user row
  deletes all of their data in this database in one statement.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_service.db import Base
from user_service.domain.consents import CONSENT_PURPOSES

MAX_LANGUAGES = 10


def _user_fk() -> Mapped[uuid.UUID]:
    """Foreign key to users.id; the child row disappears when its user is deleted."""
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


def _now_column(*, on_update: bool = False) -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now() if on_update else None,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(user_sub) BETWEEN 1 AND 255", name="user_sub_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # Identity provider "subject": the stable ID Clerk puts in every token (decision D3).
    user_sub: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = _now_column()
    updated_at: Mapped[datetime] = _now_column(on_update=True)

    # passive_deletes=True: let Postgres' ON DELETE CASCADE do the work instead of the ORM
    # loading every child row just to delete it.
    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    languages: Mapped[list["UserLanguage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserLanguage.rank",
    )
    genres: Mapped[list["UserGenre"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserGenre.genre_slug",
    )
    consents: Mapped[list["UserConsent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class UserPreferences(Base):
    """One row per onboarded user. No row = not onboarded yet (GET returns 404)."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        CheckConstraint(
            "region_code IS NULL OR region_code ~ '^[A-Z]{2}-[A-Z0-9]{1,3}$'",
            name="region_code_format",
        ),
        # "IN-AP" is only valid together with country "IN".
        CheckConstraint(
            "region_code IS NULL OR left(region_code, 3) = country_code || '-'",
            name="region_in_country",
        ),
    )

    user_id: Mapped[uuid.UUID] = _user_fk()
    country_code: Mapped[str] = mapped_column(String(2))
    region_code: Mapped[str | None] = mapped_column(String(6))
    onboarded_at: Mapped[datetime] = _now_column()
    updated_at: Mapped[datetime] = _now_column(on_update=True)

    user: Mapped[User] = relationship(back_populates="preferences")


class UserLanguage(Base):
    """Chosen languages in order of preference: rank 1 = favourite."""

    __tablename__ = "user_languages"
    __table_args__ = (
        CheckConstraint("language_code ~ '^[a-z]{2,3}$'", name="language_code_format"),
        CheckConstraint(f"rank BETWEEN 1 AND {MAX_LANGUAGES}", name="rank_range"),
        UniqueConstraint("user_id", "rank"),  # two languages can't share a rank
    )

    user_id: Mapped[uuid.UUID] = _user_fk()
    language_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    rank: Mapped[int] = mapped_column(SmallInteger)

    user: Mapped[User] = relationship(back_populates="languages")


class UserGenre(Base):
    __tablename__ = "user_genres"
    __table_args__ = (
        CheckConstraint("genre_slug ~ '^[a-z]+(-[a-z]+)*$'", name="genre_slug_format"),
    )

    user_id: Mapped[uuid.UUID] = _user_fk()
    genre_slug: Mapped[str] = mapped_column(Text, primary_key=True)

    user: Mapped[User] = relationship(back_populates="genres")


class UserConsent(Base):
    """An explicit yes/no per purpose. No row = never asked = treated as NOT granted."""

    __tablename__ = "user_consents"
    __table_args__ = (
        CheckConstraint(
            "purpose IN (" + ", ".join(f"'{p}'" for p in CONSENT_PURPOSES) + ")",
            name="purpose_known",
        ),
    )

    user_id: Mapped[uuid.UUID] = _user_fk()
    purpose: Mapped[str] = mapped_column(Text, primary_key=True)
    granted: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = _now_column(on_update=True)

    user: Mapped[User] = relationship(back_populates="consents")
