# API Contracts (v1 draft)

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

Human-readable summary. The machine-readable source of truth will be the OpenAPI files in
`contracts/openapi/` generated from code starting in Phase 1.

## 0. Conventions

- Base path `/v1`. JSON only. `snake_case` fields. Timestamps RFC 3339 UTC.
- Auth: `Authorization: Bearer <JWT>` for 🔒 endpoints. 🔑 = internal service token.
- `/v1/me/...` endpoints derive the user from the token — no user IDs in URLs.
- Pagination: `?limit=` (default 20, max 100) and opaque `?cursor=`; responses include
  `next_cursor` (null at end). Keyset pagination — stable under inserts, O(log n) per page.
- Errors: RFC 9457 problem details:

```json
{ "type": "https://errors.movie-reco.local/validation", "title": "Invalid request",
  "status": 422, "detail": "languages must contain at least 1 item",
  "instance": "/v1/me/preferences", "request_id": "6f1c…" }
```

- Every service: `GET /health` (process alive) and `GET /ready` (DB reachable, migrations at head).

## 1. user-service

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/me/preferences` | 🔒 | Get preferences; 404 if not onboarded |
| PUT | `/v1/me/preferences` | 🔒 | Create/replace preferences (idempotent upsert; creates user row on first call) |
| GET | `/v1/me/consents` | 🔒 | List consents |
| PUT | `/v1/me/consents/{purpose}` | 🔒 | Grant/withdraw |
| GET | `/v1/me/watchlist` | 🔒 | Paginated watchlist (movie IDs + added_at) |
| PUT | `/v1/me/watchlist/{movie_id}` | 🔒 | Add (idempotent; 201 created, 200 already present) |
| DELETE | `/v1/me/watchlist/{movie_id}` | 🔒 | Remove (idempotent; 204) |
| GET | `/v1/me/watchlist/contains?movie_ids=a,b` | 🔒 | Membership check for card badges (≤100 IDs) |
| DELETE | `/v1/me` | 🔒 | Delete profile and all user-service data |

```http
PUT /v1/me/preferences
{
  "country_code": "IN",
  "region_code": "IN-AP",
  "languages": ["te", "en"],          // ordered; 1..10; ISO 639-1
  "genres": ["thriller", "drama"]     // 0..5; slugs from contracts/vocab/genres.v1.json
}
→ 200
{
  "country_code": "IN", "region_code": "IN-AP",
  "languages": [{"code": "te", "rank": 1}, {"code": "en", "rank": 2}],
  "genres": ["drama", "thriller"],
  "onboarded_at": "2026-11-20T10:02:11Z", "updated_at": "2026-11-20T10:02:11Z"
}
```

Validation: `region_code` must start with `country_code + "-"`; unknown language/genre → 422.

**Implemented (step 2.4):** `GET`/`PUT /v1/me/preferences`.
- Order of checks: token (401/503) → shape (Pydantic; 422) → vocabulary rules (domain; 422)
  → database write in one transaction. A rejected PUT changes nothing.
- 422 body: `errors: [{"loc": ["body","languages",1], "msg": "Not a supported value",
  "type": "unknown_code"}]`; types: Pydantic's own, `unknown_code`, `duplicate`,
  `region_not_in_country`. Messages never echo submitted values.
- Unknown body fields are rejected (`extra="forbid"`), so a client cannot name another user.
- PUT replaces everything (omitted `region_code`/`genres` are cleared); `genres` returned
  sorted; `onboarded_at` keeps its first value.
- `AUTH_ISSUER` unset → every `/v1/me/*` call returns 503 "Authentication is not configured".

```http
GET /v1/me/watchlist?limit=2
→ 200 { "items": [ {"movie_id": "0b6c…", "added_at": "…"}, {"movie_id": "91aa…", "added_at": "…"} ],
        "next_cursor": "eyJhIjoi…" }
```

## 2. catalog-service

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/movies` | public | Search/browse: `q`, `genre`, `language`, `country`, `year_from`, `year_to`, `sort=relevance\|popularity\|release_date\|rating`, `limit`, `cursor` |
| GET | `/v1/movies/{id}` | public | Movie details |
| POST | `/v1/movies/batch-get` | public | Body `{"ids": [...]}` (≤100) → movies in requested order, `missing` list |
| GET | `/v1/genres` | public | Genre vocabulary |
| GET | `/v1/languages` | public | Languages present in catalog with counts |
| GET | `/v1/internal/movie-features` | 🔑 | Feature export: `updated_since`, `cursor`, `limit≤1000` |

Imports are **CLI commands**, not HTTP endpoints (smaller attack surface):
`uv run catalog import-tmdb --languages te,en,hi --max 5000`.

```http
GET /v1/movies?q=baahu&language=te&limit=1
→ 200
{
  "items": [{
    "id": "4d2e…", "title": "Example Title", "original_title": "…",
    "release_date": "2015-07-10", "runtime_minutes": 159,
    "original_language": "te", "spoken_languages": ["te"],
    "genres": ["action", "drama"],
    "poster_url": "https://image.tmdb.org/t/p/w342/…",
    "popularity": {"value": 0.82, "source": "tmdb", "as_of": "2026-11-18T00:00:00Z"},
    "rating": {"mean": 7.6, "count": 4100, "source": "tmdb"}
  }],
  "next_cursor": "…"
}
```

Note: `sort=relevance` (trigram/full-text rank) can't use a simple keyset cursor; for that
sort we use `limit`+`offset` capped at 500 results. Documented tradeoff.

```http
GET /v1/internal/movie-features?updated_since=2026-11-01T00:00:00Z&limit=1000
X-Service-Token: <redacted>
→ 200 { "items": [ {"movie_id": "…", "genres": [...], "original_language": "en",
          "spoken_languages": [...], "release_countries": ["IN","US"], "release_year": 2019,
          "popularity_raw": 54.3, "rating_mean": 7.1, "rating_count": 1300,
          "updated_at": "…"} ],
        "next_cursor": "…", "feature_version": 1 }
```

## 3. recommendation-service

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/me/home` | 🔒 | Homepage rows (IDs + scores + reasons) |
| GET | `/v1/me/recommendations` | 🔒 | Single surface: `surface=top_picks`, `limit` |
| GET | `/v1/movies/{id}/similar` | public | Content-similar movies (non-personal) |
| POST | `/v1/me/events` | 🔒 | Batch of ≤50 interaction events |
| DELETE | `/v1/me/events` | 🔒 | Delete all events, feature state, rec logs |
| GET | `/v1/me/profile-debug` | 🔒 (dev only flag) | Learned affinities for learning/debugging |

```http
GET /v1/me/home
→ 200
{
  "request_id": "a1b2…", "algorithm_version": "hybrid-v1", "degraded": false,
  "rows": [
    { "id": "top_picks", "title": "Top picks for you",
      "items": [{ "movie_id": "…", "score": 0.71,
                  "reasons": [{"code": "language_pref", "text": "Because you chose Telugu"},
                              {"code": "genre_affinity", "text": "You often watch Thrillers"}] }] },
    { "id": "popular_lang_te", "title": "Popular Telugu films",
      "signal": {"type": "provider_proxy", "label": "Based on TMDB global popularity"},
      "items": [ … ] },
    { "id": "popular_country_IN", "title": "Popular releases in India",
      "signal": {"type": "provider_proxy", "label": "Released in India · ranked by global popularity"},
      "items": [ … ] }
  ]
}
```

```http
POST /v1/me/events
{
  "events": [
    { "event_id": "3f6c2b2e-…", "movie_id": "…", "event_type": "impression",
      "surface": "home:top_picks", "position": 3, "rec_request_id": "a1b2…",
      "occurred_at": "2026-11-20T10:05:00Z", "is_simulated": false },
    { "event_id": "8d1a…", "movie_id": "…", "event_type": "watch_progress", "value": 0.65,
      "surface": "details", "occurred_at": "…", "is_simulated": true }
  ]
}
→ 202 { "accepted": 2, "duplicates": 0 }
→ 403 problem+json if tracking consent is not granted
```

`watch_progress` **must** have `is_simulated: true` (we have no real playback) — server rejects otherwise.

## 4. Frontend BFF routes (Next.js, browser-facing)

| Route | Purpose |
|---|---|
| `POST /api/events` | Receives browser event batches, attaches token, forwards |
| `PUT/DELETE /api/watchlist/[movieId]` | Watchlist toggles |
| `PUT /api/preferences` | Onboarding/settings submit |
| `DELETE /api/account` | Orchestrates cross-service deletion |

Pages fetch data in **server components** directly from services; route handlers exist
only for browser-initiated mutations.

## 5. Versioning & compatibility rules

- Adding optional fields / new endpoints: non-breaking, same `/v1`.
- Removing/renaming fields, changing types or semantics: new `/v2`, run both until the
  frontend migrates.
- Consumers must ignore unknown fields (tolerant reader).
