"""Preference rules (business logic). The API layer has already checked the *shape* of the
input (types, lengths, code formats); here we check the *meaning*:

* every code exists in our vocabulary (contracts/vocab)
* the region belongs to the chosen country ("IN-AP" only with "IN")
* no language or genre is listed twice

All problems are collected and reported together, so the user can fix everything at once
instead of one error per attempt.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from user_service.domain.errors import DomainValidationError, FieldError
from user_service.domain.vocabulary import Vocabulary


@dataclass(frozen=True)
class PreferencesInput:
    country_code: str
    region_code: str | None
    languages: Sequence[str]  # in order of preference: first = favourite
    genres: Sequence[str]


@dataclass(frozen=True)
class ValidPreferences:
    """Only `validate_preferences` creates these, so holding one means the rules passed."""

    country_code: str
    region_code: str | None
    languages: tuple[str, ...]  # rank = position + 1
    genres: tuple[str, ...]  # sorted: genres have no order of preference


def _check_codes(
    field: str, codes: Sequence[str], allowed: frozenset[str], errors: list[FieldError]
) -> None:
    seen: set[str] = set()
    for index, code in enumerate(codes):
        loc = ("body", field, index)
        # Messages never repeat the submitted value (project rule); `loc` says which item.
        if code in seen:
            errors.append(FieldError(loc, "Listed more than once", "duplicate"))
        elif code not in allowed:
            errors.append(FieldError(loc, "Not a supported value", "unknown_code"))
        seen.add(code)


def validate_preferences(data: PreferencesInput, vocabulary: Vocabulary) -> ValidPreferences:
    errors: list[FieldError] = []

    country_regions = vocabulary.regions_by_country.get(data.country_code)
    if country_regions is None:
        errors.append(
            FieldError(("body", "country_code"), "Not a supported country", "unknown_code")
        )
    elif data.region_code is not None and data.region_code not in country_regions:
        errors.append(
            FieldError(
                ("body", "region_code"),
                "Not a supported region of the chosen country",
                "region_not_in_country",
            )
        )

    _check_codes("languages", data.languages, vocabulary.languages, errors)
    _check_codes("genres", data.genres, vocabulary.genres, errors)

    if errors:
        raise DomainValidationError(errors)
    return ValidPreferences(
        country_code=data.country_code,
        region_code=data.region_code,
        languages=tuple(data.languages),
        genres=tuple(sorted(data.genres)),
    )
