"""Read and write a user's preferences.

Every function takes the user's `sub` (from the verified token), never a user ID from the
request. That is the ownership rule: you can only ever reach your own rows.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from user_service.domain.preferences import ValidPreferences
from user_service.models import User, UserGenre, UserLanguage, UserPreferences


@dataclass(frozen=True)
class StoredPreferences:
    country_code: str
    region_code: str | None
    languages: tuple[str, ...]  # rank order
    genres: tuple[str, ...]  # sorted
    onboarded_at: datetime
    updated_at: datetime


def get_or_create_user_id(session: Session, user_sub: str) -> uuid.UUID:
    """Find the user row for this identity, creating it on first use.

    INSERT ... ON CONFLICT DO NOTHING is safe even if two first requests from the same user
    arrive at the same moment: one inserts, the other quietly does nothing, both then read
    the same row. (Check-then-insert in Python would race and fail with a duplicate key.)
    """
    session.execute(
        pg_insert(User)
        .values(user_sub=user_sub)
        .on_conflict_do_nothing(index_elements=["user_sub"])
    )
    return session.scalars(select(User.id).where(User.user_sub == user_sub)).one()


def replace_preferences(session: Session, user_sub: str, prefs: ValidPreferences) -> None:
    """PUT semantics: after this call the stored preferences are exactly `prefs`.

    Must run inside a transaction: the deletes and inserts become visible together or not
    at all, so nobody ever sees a half-written state (e.g. languages deleted, none added).
    """
    user_id = get_or_create_user_id(session, user_sub)

    # Upsert the single preferences row. onboarded_at keeps its first value forever.
    upsert = pg_insert(UserPreferences).values(
        user_id=user_id, country_code=prefs.country_code, region_code=prefs.region_code
    )
    session.execute(
        upsert.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "country_code": upsert.excluded.country_code,
                "region_code": upsert.excluded.region_code,
                "updated_at": func.now(),
            },
        )
    )

    # Replace the lists: delete all, insert the new ones. Deleting first also avoids
    # clashing with the unique (user_id, rank) rule when the order changes.
    session.execute(delete(UserLanguage).where(UserLanguage.user_id == user_id))
    session.execute(
        insert(UserLanguage),
        [
            {"user_id": user_id, "language_code": code, "rank": rank}
            for rank, code in enumerate(prefs.languages, start=1)
        ],
    )
    session.execute(delete(UserGenre).where(UserGenre.user_id == user_id))
    if prefs.genres:
        session.execute(
            insert(UserGenre),
            [{"user_id": user_id, "genre_slug": slug} for slug in prefs.genres],
        )


def get_preferences(session: Session, user_sub: str) -> StoredPreferences | None:
    """None when this user has never completed onboarding (no preferences row)."""
    row = session.execute(
        select(UserPreferences)
        .join(User, User.id == UserPreferences.user_id)
        .where(User.user_sub == user_sub)
    ).scalar_one_or_none()
    if row is None:
        return None
    languages = session.scalars(
        select(UserLanguage.language_code)
        .where(UserLanguage.user_id == row.user_id)
        .order_by(UserLanguage.rank)
    ).all()
    genres = session.scalars(
        select(UserGenre.genre_slug)
        .where(UserGenre.user_id == row.user_id)
        .order_by(UserGenre.genre_slug)
    ).all()
    return StoredPreferences(
        country_code=row.country_code,
        region_code=row.region_code,
        languages=tuple(languages),
        genres=tuple(genres),
        onboarded_at=row.onboarded_at,
        updated_at=row.updated_at,
    )
