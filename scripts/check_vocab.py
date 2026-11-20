"""Validate the controlled vocabularies in contracts/vocab/.

Standard library only, so it runs anywhere Python 3.10+ is installed (CI, your laptop)
without installing anything.

Usage (from the repo root):
    python scripts/check_vocab.py              # check contracts/vocab
    python scripts/check_vocab.py some/dir     # check another folder (used to test the checker)

Exit code 0 = all files valid, 1 = problems found (each one is printed).
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "contracts" / "vocab"
FILE_NAME = re.compile(r"^(?P<vocabulary>[a-z]+)\.v(?P<version>[1-9][0-9]*)\.json$")

LANGUAGE_CODE = re.compile(r"^[a-z]{2}$")  # ISO 639-1, e.g. "te"
GENRE_SLUG = re.compile(r"^[a-z]+(-[a-z]+)*$")  # e.g. "science-fiction"
COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2, e.g. "IN"
REGION_CODE = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")  # ISO 3166-2, e.g. "IN-AP"


def check_items(
    items: object, label: str, code_pattern: re.Pattern[str], extra_fields: tuple[str, ...]
) -> list[str]:
    """Rules shared by every list: shape, code format, non-empty names, unique and sorted."""
    if not isinstance(items, list) or not items:
        return [f"{label}: must be a non-empty list"]
    errors: list[str] = []
    codes: list[str] = []
    for index, item in enumerate(items):
        where = f"{label}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object")
            continue
        code = item.get("code")
        if not isinstance(code, str) or not code_pattern.fullmatch(code):
            errors.append(f"{where}: code {code!r} does not match {code_pattern.pattern}")
            continue
        codes.append(code)
        for field in ("name", *extra_fields):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where} ({code}): '{field}' must be a non-empty string")
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        errors.append(f"{label}: duplicate codes {duplicates}")
    if codes != sorted(codes):
        errors.append(f"{label}: items must be sorted by code (keeps diffs small and stable)")
    return errors


def check_languages(data: dict[str, object]) -> list[str]:
    return check_items(data.get("items"), "languages", LANGUAGE_CODE, ("native_name",))


def check_genres(data: dict[str, object]) -> list[str]:
    return check_items(data.get("items"), "genres", GENRE_SLUG, ())


def check_regions(data: dict[str, object]) -> list[str]:
    countries = data.get("items")
    errors = check_items(countries, "regions", COUNTRY_CODE, ())
    if not isinstance(countries, list):
        return errors
    for country in countries:
        if not isinstance(country, dict) or not isinstance(country.get("code"), str):
            continue  # already reported above
        code = country["code"]
        regions = country.get("regions")
        if not isinstance(regions, list):
            errors.append(f"regions ({code}): 'regions' must be a list (may be empty)")
            continue
        if regions:
            errors += check_items(regions, f"regions.{code}", REGION_CODE, ())
        # A region must belong to the country it is listed under: "IN-AP" only under "IN".
        errors += [
            f"regions.{code}: {r['code']!r} does not start with '{code}-'"
            for r in regions
            if isinstance(r, dict)
            and isinstance(r.get("code"), str)
            and not r["code"].startswith(f"{code}-")
        ]
    return errors


CHECKERS: dict[str, Callable[[dict[str, object]], list[str]]] = {
    "languages": check_languages,
    "genres": check_genres,
    "regions": check_regions,
}


def check_file(path: Path) -> list[str]:
    match = FILE_NAME.fullmatch(path.name)
    if match is None:
        return [f"{path.name}: file name must look like '<vocabulary>.v<N>.json'"]
    vocabulary, version = match["vocabulary"], int(match["version"])
    checker = CHECKERS.get(vocabulary)
    if checker is None:
        return [f"{path.name}: unknown vocabulary {vocabulary!r} (add a checker for it)"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{path.name}: not valid UTF-8 JSON ({exc})"]
    if not isinstance(data, dict):
        return [f"{path.name}: top level must be an object"]

    errors: list[str] = []
    if data.get("vocabulary") != vocabulary:
        errors.append(f"'vocabulary' must be {vocabulary!r} to match the file name")
    if data.get("version") != version:
        errors.append(f"'version' must be {version} to match the file name")
    for field in ("standard", "description"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"'{field}' must be a non-empty string")
    errors += checker(data)
    return [f"{path.name}: {e}" for e in errors]


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    files = sorted(folder.glob("*.json"))
    if not files:
        print(f"no vocabulary files found in {folder}")
        return 1
    errors = [error for path in files for error in check_file(path)]
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        return 1
    print(f"OK: {len(files)} vocabulary files valid ({', '.join(p.name for p in files)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
