# Service Communication

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

## 1. Principles

1. **Synchronous HTTP/JSON first.** Easy to debug with Swagger and curl.
2. **Every call has a timeout.** A slow dependency must not hang the caller.
3. **Retry only safe, idempotent operations** (GET, PUT, DELETE, and POSTs that carry an
   idempotency key), at most 2 retries with exponential backoff + jitter.
4. **Degrade, don't fail**, where a sensible fallback exists (see `architecture.md` §6).
5. **Contracts, not shared code.** Services share OpenAPI files in `contracts/`, never
   Python modules or database tables.

> **Plain-language concept — idempotency.** An operation is idempotent if doing it twice
> has the same effect as doing it once. "Add movie 42 to my watchlist" via `PUT` is
> idempotent: the second call finds it already there. "Record a click" is *not*, unless the
> client sends a unique `event_id` and the server ignores repeats. That's why only
> idempotent calls may be retried blindly.

## 2. Call map

| # | Caller → Callee | Endpoint | Auth | Timeout | Retry | On failure |
|---|---|---|---|---|---|---|
| 1 | BFF → user-service | `GET /v1/me/preferences` | user JWT | 800 ms | 1 | redirect to onboarding only on 404; otherwise error banner |
| 2 | BFF → recommendation | `GET /v1/me/home` | user JWT | 1500 ms | 0 | fallback popular rows from catalog (#4) |
| 3 | BFF → catalog | `POST /v1/movies/batch-get` | none (public data) | 800 ms | 1 | card placeholders |
| 4 | BFF → catalog | `GET /v1/movies?...` | none | 800 ms | 1 | error state |
| 5 | BFF → user-service | watchlist `PUT/DELETE/GET` | user JWT | 800 ms | 1 (all idempotent) | toast error |
| 6 | BFF → recommendation | `POST /v1/me/events` (batched) | user JWT | 1000 ms | 2 (idempotent via `event_id`) | keep in browser queue, drop after 3 attempts |
| 7 | recommendation → user-service | `GET /v1/me/preferences` | forwarded user JWT | 300 ms | 1 | use learned affinities / global popularity, `degraded: true` |
| 8 | recommendation → catalog | `GET /v1/internal/movie-features?updated_since=&cursor=` | service credential | 5 s | 2 | keep stale features, log warning |
| 9 | user-service → catalog | `GET /v1/movies/{id}` (validate on watchlist add) | none | 500 ms | 1 | 503 to caller (don't add unverifiable IDs) |
| 10 | BFF → each service | `DELETE /v1/me` / `DELETE /v1/me/events` | user JWT | 2 s | 2 (idempotent) | show "deletion pending", retry on next sign-in |

## 3. Sequence: homepage load

```
Browser      Next.js server (BFF)        recommendation        user-service     catalog
  │ GET /home      │                            │                    │              │
  │───────────────▶│ verify session (IdP SDK)   │                    │              │
  │                │ GET /v1/me/home  (JWT) ───▶│                    │              │
  │                │                            │ GET /v1/me/prefs ─▶│              │
  │                │                            │◀── prefs ──────────│              │
  │                │                            │ rank using local   │              │
  │                │                            │ features+events    │              │
  │                │◀── rows of {movie_id,      │                    │              │
  │                │      score, reasons}       │                    │              │
  │                │ POST /v1/movies/batch-get (unique IDs) ─────────────────────────▶│
  │                │◀─────────────────────────── titles, posters ─────────────────────│
  │◀── HTML (rows) │                            │                    │              │
```

**Why does the recommender return IDs and not full movies?** It keeps the recommender
from becoming a second source of truth for titles/posters. The BFF "hydrates" IDs in one
batch call. One extra hop, but ownership stays clean.

## 4. Sequence: interaction event

```
Browser                         BFF /api/events               recommendation-service
  │ card ≥50% visible ≥1s → queue impression (event_id = uuid v4)
  │ every 10 s or on page hide: sendBeacon/POST batch ≤50 ─▶│
  │                                │ attach JWT, POST /v1/me/events ─▶│
  │                                │                                  │ check consent (cached prefs)
  │                                │                                  │ INSERT ... ON CONFLICT (event_id) DO NOTHING
  │                                │                                  │ update user_feature_state (same transaction)
  │                                │◀── 202 {accepted: n, duplicates: m}
```

Updating affinities in the same transaction keeps Phases 5's design simple. If this
becomes slow, Phase 7 moves the update to an asynchronous worker (see §6).

## 5. Service-to-service authentication

| Call type | Mechanism | Why |
|---|---|---|
| On behalf of a user (#7) | Forward the user's JWT; callee validates normally | Callee enforces the user's own ownership rules; no extra privilege |
| Public catalog reads (#3, #4, #9) | None | Movie metadata isn't sensitive |
| Internal feature export (#8) | **Dev:** static per-caller token in env (`X-Service-Token`), compared in constant time, only on `/v1/internal/*`. **Later:** IdP machine-to-machine (OAuth2 client-credentials) JWT | Minimal setup now; clear upgrade path. Decision D4. |

## 6. When we would introduce asynchronous messaging (Phase 7 gate)

We add a broker **only** when at least one of these is observed and written up:

1. Events must be accepted while recommendation-service is unavailable (durability gap).
2. Feature updates per event make `POST /v1/me/events` exceed its latency budget.
3. A second consumer of the same events appears (e.g. analytics, training pipeline).

Before adopting, we must specify: event schema (versioned in `contracts/events/`),
idempotency key (`event_id`), at-least-once delivery semantics, retry policy, dead-letter
queue handling, and ordering assumptions. A transactional outbox in the producing
service is the likely pattern. Candidate tech then: Redis Streams or RabbitMQ (simplest);
Kafka only if replay/high-throughput needs are demonstrated.

## 7. Contract workflow

1. FastAPI generates OpenAPI from Pydantic models.
2. A script exports it to `contracts/openapi/<service>.v1.json`.
3. CI fails if the committed contract differs from the generated one (forces review of
   API changes in PRs).
4. The frontend generates TypeScript types from those files (`openapi-typescript`), so
   type mismatches fail `tsc`.
