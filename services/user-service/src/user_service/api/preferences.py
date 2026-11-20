"""HTTP layer for preferences: translate between JSON and the domain, nothing more.

    request JSON --(Pydantic: shape)--> domain rules (meaning) --> repository (SQL)

Every route here is protected (`CurrentUser`), and every lookup uses the token's `sub`.
There is deliberately no user ID anywhere in the URL or body: "/v1/me" can only ever mean
the caller, so one user cannot even *ask* for another user's data.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from user_service.auth import CurrentUser
from user_service.db import get_session
from user_service.domain.preferences import PreferencesInput, validate_preferences
from user_service.domain.vocabulary import load_vocabulary
from user_service.errors import problem_doc
from user_service.models import MAX_LANGUAGES
from user_service.repositories import preferences as repo
from user_service.repositories.preferences import StoredPreferences

MAX_GENRES = 5

router = APIRouter(prefix="/v1/me", tags=["preferences"])

DbSession = Annotated[Session, Depends(get_session)]

AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: problem_doc("Missing, invalid or expired token"),
    503: problem_doc("Authentication or database temporarily unavailable"),
}


class PreferencesRequest(BaseModel):
    """What the client sends. Shape checks only; vocabulary checks happen in the domain."""

    # extra="forbid": unknown fields (e.g. a smuggled "user_sub") are rejected, not ignored.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "country_code": "IN",
                "region_code": "IN-AP",
                "languages": ["te", "en"],
                "genres": ["thriller", "drama"],
            }
        },
    )

    country_code: str = Field(pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2")
    region_code: str | None = Field(
        default=None, pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$", description="ISO 3166-2, optional"
    )
    languages: list[Annotated[str, Field(pattern=r"^[a-z]{2,3}$")]] = Field(
        min_length=1,
        max_length=MAX_LANGUAGES,
        description="ISO 639-1 codes in order of preference (first = favourite)",
    )
    genres: list[Annotated[str, Field(pattern=r"^[a-z]+(-[a-z]+)*$")]] = Field(
        default_factory=list, max_length=MAX_GENRES, description="Genre slugs, any order"
    )


class RankedLanguage(BaseModel):
    code: str
    rank: int


class PreferencesResponse(BaseModel):
    country_code: str
    region_code: str | None
    languages: list[RankedLanguage]
    genres: list[str]
    onboarded_at: datetime
    updated_at: datetime

    @classmethod
    def from_stored(cls, stored: StoredPreferences) -> "PreferencesResponse":
        return cls(
            country_code=stored.country_code,
            region_code=stored.region_code,
            languages=[
                RankedLanguage(code=code, rank=rank)
                for rank, code in enumerate(stored.languages, start=1)
            ],
            genres=list(stored.genres),
            onboarded_at=stored.onboarded_at,
            updated_at=stored.updated_at,
        )


@router.get(
    "/preferences",
    response_model=PreferencesResponse,
    summary="Get my preferences",
    responses={**AUTH_ERRORS, 404: problem_doc("Not onboarded yet (no preferences saved)")},
)
def get_my_preferences(user: CurrentUser, session: DbSession) -> PreferencesResponse:
    stored = repo.get_preferences(session, user.sub)
    if stored is None:
        raise HTTPException(status_code=404, detail="No preferences saved yet")
    return PreferencesResponse.from_stored(stored)


@router.put(
    "/preferences",
    response_model=PreferencesResponse,
    summary="Create or replace my preferences",
    description=(
        "Idempotent: sending the same body again leaves the same preferences. "
        "Creates the user record on first call."
    ),
    responses={**AUTH_ERRORS, 422: problem_doc("Invalid shape or unsupported code")},
)
def put_my_preferences(
    body: PreferencesRequest, user: CurrentUser, session: DbSession
) -> PreferencesResponse:
    valid = validate_preferences(
        PreferencesInput(
            country_code=body.country_code,
            region_code=body.region_code,
            languages=body.languages,
            genres=body.genres,
        ),
        load_vocabulary(),
    )
    with session.begin():  # all-or-nothing; committed before we respond
        repo.replace_preferences(session, user.sub, valid)
        stored = repo.get_preferences(session, user.sub)
    assert stored is not None  # we just wrote it in the same transaction
    return PreferencesResponse.from_stored(stored)
