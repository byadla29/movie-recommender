"""Consent rules.

Privacy by default: if a user has never answered, the answer is NO. We store a row only
when the user actively chooses, so "no row" can only ever mean "never agreed".

Purposes are listed here once. The database CHECK constraint and the API's allowed path
values are built from this list (a unit test checks they agree).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, get_args

# personalization_tracking: may we record impressions/clicks/likes to tailor recommendations?
ConsentPurpose = Literal["personalization_tracking"]
CONSENT_PURPOSES: tuple[str, ...] = get_args(ConsentPurpose)

DEFAULT_GRANTED = False


@dataclass(frozen=True)
class ConsentState:
    purpose: str
    granted: bool
    updated_at: datetime | None  # None = the user has never been asked / never answered


def effective_consents(stored: Mapping[str, tuple[bool, datetime]]) -> list[ConsentState]:
    """One entry per known purpose: the stored answer, or the privacy default (NO)."""
    return [
        ConsentState(purpose, *stored[purpose])
        if purpose in stored
        else ConsentState(purpose, DEFAULT_GRANTED, None)
        for purpose in CONSENT_PURPOSES
    ]
