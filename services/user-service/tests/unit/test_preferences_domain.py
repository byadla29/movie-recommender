"""Preference rules with plain values: no HTTP, no database."""

import pytest

from user_service.domain.errors import DomainValidationError, FieldError
from user_service.domain.preferences import PreferencesInput, validate_preferences
from user_service.domain.vocabulary import Vocabulary, load_vocabulary

VOCAB = load_vocabulary()


def prefs(**overrides: object) -> PreferencesInput:
    values: dict[str, object] = {
        "country_code": "IN",
        "region_code": "IN-AP",
        "languages": ["te", "en"],
        "genres": ["thriller", "drama"],
    }
    values.update(overrides)
    return PreferencesInput(**values)  # type: ignore[arg-type]


def errors_of(data: PreferencesInput, vocab: Vocabulary = VOCAB) -> list[FieldError]:
    with pytest.raises(DomainValidationError) as caught:
        validate_preferences(data, vocab)
    return caught.value.errors


def test_vocabulary_is_loaded_from_the_contract_copies() -> None:
    assert len(VOCAB.languages) == 22
    assert len(VOCAB.genres) == 18
    assert len(VOCAB.regions_by_country) == 7
    assert "te" in VOCAB.languages
    assert "IN-AP" in VOCAB.regions_by_country["IN"]
    assert VOCAB.regions_by_country["US"] == frozenset()


def test_valid_preferences_keep_language_order_and_sort_genres() -> None:
    valid = validate_preferences(prefs(languages=["te", "hi", "en"]), VOCAB)

    assert valid.languages == ("te", "hi", "en")  # order = preference, must not change
    assert valid.genres == ("drama", "thriller")  # genres have no order: store sorted


def test_region_is_optional() -> None:
    assert validate_preferences(prefs(region_code=None), VOCAB).region_code is None


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"country_code": "ZZ"}, FieldError(("body", "country_code"), "", "unknown_code")),
        (
            {"region_code": "IN-ZZ"},  # right format, not a real Indian region
            FieldError(("body", "region_code"), "", "region_not_in_country"),
        ),
        (
            {"country_code": "US", "region_code": "IN-AP"},  # region of another country
            FieldError(("body", "region_code"), "", "region_not_in_country"),
        ),
        (
            {"languages": ["te", "xx"]},
            FieldError(("body", "languages", 1), "", "unknown_code"),
        ),
        (
            {"languages": ["te", "en", "te"]},
            FieldError(("body", "languages", 2), "", "duplicate"),
        ),
        (
            {"genres": ["thriller", "masala"]},
            FieldError(("body", "genres", 1), "", "unknown_code"),
        ),
    ],
)
def test_rule_violations_point_at_the_exact_field(
    overrides: dict[str, object], expected: FieldError
) -> None:
    [error] = errors_of(prefs(**overrides))

    assert (error.loc, error.type) == (expected.loc, expected.type)


def test_all_problems_are_reported_together() -> None:
    errors = errors_of(prefs(country_code="ZZ", languages=["xx"], genres=["masala"]))

    assert [e.loc for e in errors] == [
        ("body", "country_code"),
        ("body", "languages", 0),
        ("body", "genres", 0),
    ]


def test_error_messages_do_not_repeat_the_submitted_value() -> None:
    errors = errors_of(prefs(languages=["zz"], genres=["secretgenre"]))

    assert all("zz" not in e.msg and "secretgenre" not in e.msg for e in errors)
