"""Things every protected route needs: a database session and documented auth errors."""

from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from user_service.db import get_session
from user_service.errors import problem_doc

DbSession = Annotated[Session, Depends(get_session)]

AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: problem_doc("Missing, invalid or expired token"),
    503: problem_doc("Authentication or database temporarily unavailable"),
}
