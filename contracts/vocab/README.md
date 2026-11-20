# Controlled vocabularies

The official lists of allowed values shared by all services. They are **contracts**, like
the OpenAPI files: services read and validate against them, but no code is shared (D7).

| File | Values | Standard | Example |
|---|---|---|---|
| `languages.v1.json` | languages users can prefer / movies can have | ISO 639-1 | `te` = Telugu |
| `genres.v1.json` | our genre slugs (TMDB/MovieLens genres are mapped onto these) | project slugs | `science-fiction` |
| `regions.v1.json` | countries, each with optional regions | ISO 3166-1 / 3166-2 | `IN`, `IN-AP` |

## Who uses them
- **user-service** — rejects unknown languages/genres/regions in preferences (422), locally,
  with no network call to another service.
- **catalog-service** (Phase 3) — maps imported provider genres/languages onto these codes and
  serves them to the frontend (`GET /v1/genres`, `GET /v1/languages`).
- **recommendation-service** (Phase 4) — genre/language order defines feature-vector slots.

## Rules for changing a vocabulary
- `python scripts/check_vocab.py` must pass (CI runs it): valid codes, unique, sorted by code,
  every region starts with its country code.
- **Adding** an item is backward-compatible: keep the version. Roll out to services that
  *validate* (user-service, catalog) before the frontend offers the new value, otherwise users
  get a 422.
- **Removing or renaming** a code is breaking: create `<name>.v2.json`, migrate stored data,
  then retire v1. Stored codes in databases must never silently become invalid.

Note: India's ISO 3166-2 codes use the 2023 revision (`IN-CG`, `IN-OD`, `IN-TS`, `IN-UK`).
