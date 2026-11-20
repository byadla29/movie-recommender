"""Consent endpoints: see and change "may we track my interactions?".

GET always answers for every known purpose. Never answered = NO (privacy by default), and
reading creates no data: a user who only looks has no row in our database.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel, ConfigDict, StrictBool

from user_service.api.deps import AUTH_ERRORS, DbSession
from user_service.auth import CurrentUser
from user_service.domain.consents import ConsentPurpose, ConsentState, effective_consents
from user_service.errors import problem_doc
from user_service.repositories import consents as repo

router = APIRouter(prefix="/v1/me", tags=["consents"])


class ConsentResponse(BaseModel):
    purpose: str
    granted: bool
    updated_at: datetime | None  # null = never answered (treated as not granted)

    @classmethod
    def from_state(cls, state: ConsentState) -> "ConsentResponse":
        return cls(purpose=state.purpose, granted=state.granted, updated_at=state.updated_at)


class ConsentsResponse(BaseModel):
    consents: list[ConsentResponse]


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"granted": True}})

    # StrictBool: only JSON true/false. "yes", 1 or "true" are rejected, because consent
    # must be an explicit, unambiguous choice, never a guess from a loosely typed value.
    granted: StrictBool


def _current(session: DbSession, user_sub: str) -> list[ConsentState]:
    return effective_consents(repo.get_stored_consents(session, user_sub))


@router.get(
    "/consents",
    response_model=ConsentsResponse,
    summary="List my consent choices",
    responses=AUTH_ERRORS,
)
def get_my_consents(user: CurrentUser, session: DbSession) -> ConsentsResponse:
    return ConsentsResponse(
        consents=[ConsentResponse.from_state(s) for s in _current(session, user.sub)]
    )


@router.put(
    "/consents/{purpose}",
    response_model=ConsentResponse,
    summary="Grant or withdraw consent for one purpose",
    description="Idempotent. Withdrawing is as easy as granting: send granted=false.",
    responses={**AUTH_ERRORS, 422: problem_doc("Unknown purpose or invalid body")},
)
def put_my_consent(
    purpose: Annotated[ConsentPurpose, Path(description="What the consent is for")],
    body: ConsentRequest,
    user: CurrentUser,
    session: DbSession,
) -> ConsentResponse:
    with session.begin():
        repo.set_consent(session, user.sub, purpose, body.granted)
        states = _current(session, user.sub)
    [state] = [s for s in states if s.purpose == purpose]
    return ConsentResponse.from_state(state)
