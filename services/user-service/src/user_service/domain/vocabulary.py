"""The allowed codes, loaded from the vocabulary contract files.

The JSON files in `user_service/vocab/` are copies of `contracts/vocab/` made by
`scripts/sync-vocab.sh` (CI fails if they drift). Never edit the copies by hand.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class Vocabulary:
    languages: frozenset[str]
    genres: frozenset[str]
    # country code -> its region codes (empty set = country has no listed regions)
    regions_by_country: dict[str, frozenset[str]]


def _items(file_name: str) -> list[dict[str, Any]]:
    text = files("user_service").joinpath("vocab", file_name).read_text(encoding="utf-8")
    items: list[dict[str, Any]] = json.loads(text)["items"]
    return items


@lru_cache
def load_vocabulary() -> Vocabulary:
    """Read the files once per process; they only change with a new release."""
    return Vocabulary(
        languages=frozenset(item["code"] for item in _items("languages.v1.json")),
        genres=frozenset(item["code"] for item in _items("genres.v1.json")),
        regions_by_country={
            country["code"]: frozenset(region["code"] for region in country["regions"])
            for country in _items("regions.v1.json")
        },
    )
