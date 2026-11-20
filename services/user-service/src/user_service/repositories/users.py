"""The `users` row: one per identity (`user_sub` = the token's `sub`)."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from user_service.models import User


def find_user_id(session: Session, user_sub: str) -> uuid.UUID | None:
    """Look up without creating: reading must never create data about someone."""
    return session.scalars(select(User.id).where(User.user_sub == user_sub)).one_or_none()


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


def delete_user(session: Session, user_sub: str) -> bool:
    """Delete the user and, through ON DELETE CASCADE, every row that belongs to them.

    Returns whether a row existed. Callers treat "already gone" as success (idempotent).
    """
    result = session.execute(delete(User).where(User.user_sub == user_sub).returning(User.id))
    return result.first() is not None
