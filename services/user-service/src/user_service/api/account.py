"""Delete my account: remove everything user-service stores about the caller.

Scope: only user-service's own data (profile, preferences, languages, genres, consents).
Other services delete their own data through their own endpoints; the BFF calls each one
(see docs/architecture.md, "Account deletion"). The identity at Clerk is separate too.
"""

import logging

from fastapi import APIRouter, Response

from user_service.api.deps import AUTH_ERRORS, DbSession
from user_service.auth import CurrentUser
from user_service.repositories import users as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["account"])


@router.delete(
    "/me",
    status_code=204,
    response_class=Response,
    summary="Delete my profile and all my user-service data",
    description=(
        "Idempotent: deleting an account that is already gone (or never existed) also "
        "returns 204, so a retry after a timeout is always safe."
    ),
    responses=AUTH_ERRORS,
)
def delete_me(user: CurrentUser, session: DbSession) -> Response:
    with session.begin():
        existed = repo.delete_user(session, user.sub)
    # No user identifier in the log: after deletion we keep nothing that points to them.
    logger.info("account deleted", extra={"had_data": existed})
    return Response(status_code=204)
