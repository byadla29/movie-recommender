"""Read and write consent answers. Only the token's `sub` identifies the user."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from user_service.models import User, UserConsent
from user_service.repositories.users import get_or_create_user_id


def get_stored_consents(session: Session, user_sub: str) -> dict[str, tuple[bool, datetime]]:
    """Answers the user actually gave: {purpose: (granted, updated_at)}. Creates nothing."""
    rows = session.execute(
        select(UserConsent.purpose, UserConsent.granted, UserConsent.updated_at)
        .join(User, User.id == UserConsent.user_id)
        .where(User.user_sub == user_sub)
    ).all()
    return {purpose: (granted, updated_at) for purpose, granted, updated_at in rows}


def set_consent(session: Session, user_sub: str, purpose: str, granted: bool) -> None:
    """Record the user's answer (insert or overwrite). Run inside a transaction."""
    user_id = get_or_create_user_id(session, user_sub)
    upsert = pg_insert(UserConsent).values(user_id=user_id, purpose=purpose, granted=granted)
    session.execute(
        upsert.on_conflict_do_update(
            index_elements=["user_id", "purpose"],
            set_={"granted": upsert.excluded.granted, "updated_at": func.now()},
        )
    )
