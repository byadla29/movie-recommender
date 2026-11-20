# Architecture

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

## 1. Overview

```
                         ┌──────────────────────────────┐
   Browser ──HTTPS──────▶│  frontend (Next.js App Router)│
      │                  │  UI + BFF (server components, │
      │  sign-in UI      │  route handlers under /api)   │
      ▼                  └───────┬───────────┬──────────┬┘
 ┌───────────────┐   user JWT    │           │          │  user JWT
 │ Identity      │◀── JWKS ──────┼───────────┼──────────┼─── (each service
 │ Provider (IdP)│   (public     │           │          │     validates)
 │ e.g. Clerk    │    keys)      ▼           ▼          ▼
 └───────────────┘      ┌────────────┐ ┌────────────┐ ┌──────────────────────┐
                        │user-service│ │catalog-svc │ │recommendation-service│
                        │ FastAPI    │ │ FastAPI    │ │ FastAPI + NumPy      │
                        └─────┬──────┘ └─────┬──────┘ └───┬──────────┬───────┘
                              │              │   ▲        │          │
                              │              │   │ feature│ prefs    │
                              │              │   └────────┘ (HTTP)   │
                              │              │   sync (HTTP)  ────────┘──▶ user-service
                              ▼              ▼                 ▼
                         ┌─────────┐   ┌──────────┐      ┌─────────┐
                         │ user_db │   │catalog_db│      │ reco_db │
                         └─────────┘   └──────────┘      └─────────┘
                         (one Postgres server locally, three databases, three roles)

 Offline jobs (CLI, run manually or by cron later):
   catalog-service:  import-tmdb / import-movielens   → catalog_db
   recommendation:   sync-features, compute-popularity, evaluate → reco_db / reports
```

## 2. Components and responsibilities

| Component | Owns | Does NOT do |
|---|---|---|
| **frontend** (Next.js) | UI, session handling via IdP SDK, BFF aggregation (calls services server-side, hydrates IDs into cards), event batching from browser | Business rules, ranking, direct DB access |
| **user-service** | Profile, country/region, languages, genres, consents, watchlist | Movie metadata, recommendations |
| **catalog-service** | Movie metadata, genres, languages, countries, external IDs, source metrics (TMDB popularity, MovieLens aggregates), search, import jobs | User data, personalization |
| **recommendation-service** | Interaction events, user feature state, a *read-model copy* of movie features, popularity stats, candidate generation, ranking, explanations, evaluation | Being the source of truth for movie metadata or preferences |
| **Identity provider** | Credentials, sign-up/in/out, MFA, issuing JWTs | Application data |
| **PostgreSQL** | Three databases (`user_db`, `catalog_db`, `reco_db`), each with its own login role | Cross-database joins (impossible by design: separate DBs + roles) |

## 3. Why these boundaries (short version — full record in `adr/0001-service-boundaries.md`)

- They follow **data ownership**: who is the source of truth for each fact.
- They change for different reasons: the catalog changes when we import data; the
  recommender changes when we tune algorithms; profiles change when users edit them.
- The recommender is the most experimental part. Isolating it means a bad algorithm
  deploy can't corrupt profiles or the catalog, and the homepage can fall back to catalog
  popularity if it fails.

**Honest tradeoff:** for one developer, three services cost more than a modular monolith
(more containers, network calls, contracts). We accept this because learning service
communication is an explicit goal. We keep the cost down by sharing *nothing but
contracts* and keeping each service small.

## 4. Communication summary

Detail in `service-communication.md`.

- Browser → **only** the frontend. Backend services are not publicly exposed (in local
  Compose they publish ports to localhost only for Swagger/debugging).
- Frontend (server side) → services over HTTP/JSON with the user's JWT in
  `Authorization: Bearer`.
- recommendation-service → user-service (`GET /v1/me/preferences`, forwarding the user's JWT).
- recommendation-service → catalog-service (`GET /v1/internal/movie-features`, service
  credential) on a schedule to refresh its read model.
- No broker in Phases 1–6. Introduced in Phase 7 only if a concrete need is shown (e.g.
  events must be accepted while recommendation-service is down).

## 5. Data ownership

| Data | Source of truth | Copies elsewhere | How copies are refreshed |
|---|---|---|---|
| Profile, prefs, consents, watchlist | user-service | none persisted (rec-service fetches prefs per request) | n/a |
| Movie metadata | catalog-service | rec-service `movie_features` (derived subset) | periodic pull by `updated_since` cursor |
| Interaction events, user affinities | recommendation-service | none | n/a |
| Controlled vocabularies (genre slugs, ISO codes) | `contracts/vocab/` (versioned files in Git) | each service validates against them | release of a new contract version |
| Credentials, email | IdP | none | n/a |

**User identity across services:** every service keys user data by the IdP token's
`sub` claim (stored as `user_sub TEXT`). This avoids a lookup hop on every request. Cost:
migrating IdPs later needs a mapping table. (Decision D3 in `implementation-plan.md`.)

## 6. Failure modes and degradation

| Failure | Effect | Mitigation |
|---|---|---|
| recommendation-service down/slow (>1.5 s) | No personalized rows | BFF falls back to catalog `GET /v1/movies?sort=popularity` rows labeled "Popular" |
| user-service down when rec-service needs prefs | Can't personalize by explicit prefs | rec-service uses its stored learned affinities; if none, global popularity; response flags `degraded: true` |
| catalog-service down | Can't hydrate cards, search, or details | BFF shows error state for those sections; watchlist IDs still listed with retry |
| catalog feature sync fails | rec-service uses stale features | Last successful `synced_at` exposed on `/ready` details; stale > 24 h logs a warning |
| IdP JWKS unreachable | Can't validate new tokens | Key set cached ~5 min (re-fetched on unknown `kid`); fetch failure → 503 + `Retry-After` (not 401: the token may be fine); unknown `kid` → 401; never "allow" |
| Duplicate event submissions (retries) | Double counting | `event_id` primary key → `ON CONFLICT DO NOTHING` |
| Postgres down | Service not ready | `/ready` fails; Compose healthchecks; BFF shows error state |

## 7. Cross-cutting concerns

- **Auth:** each service validates the JWT itself: RS256 signature via JWKS, `iss`, `exp`,
  `nbf`, `iat`, `sub`; `aud` and `azp` when configured (Clerk session tokens carry `azp`,
  not `aud`). Failures → 401 with one generic message; reason logged, token never logged.
  Unset `AUTH_ISSUER` → protected endpoints 503 (fail closed). Implemented in
  user-service `auth.py` (step 2.3); other services copy the pattern when they need it (D7).
  Authorization = resource ownership by `sub`; "my" endpoints use `/v1/me/...` so there
  is no user ID in the URL to tamper with (prevents IDOR bugs).
- **Errors:** RFC 9457 `application/problem+json` everywhere.
- **Request IDs:** BFF generates `X-Request-ID`; services log it and forward it.
- **Config:** 12-factor env vars; `.env.example` per service with placeholders.
- **Logging:** JSON logs; never log tokens, emails, or full request bodies of events.
- **Versioning:** URL prefix `/v1`; breaking changes → `/v2` side by side.

## 8. Technology choices (and what we are deliberately *not* using yet)

| Need | Choice | Not now (and why) |
|---|---|---|
| UI/BFF | Next.js App Router, TS, Tailwind | Separate API gateway — BFF covers aggregation; add gateway only if multiple clients appear |
| Services | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic | — |
| Search | Postgres full-text + `pg_trgm` | Elasticsearch/OpenSearch — overkill below ~millions of docs |
| ML | NumPy, pandas, scikit-learn, SciPy sparse | Vector DB — brute-force cosine over ≤50k vectors takes milliseconds |
| Async | None (sync HTTP) | Kafka/RabbitMQ — no requirement yet (see Phase 7 criteria) |
| Cache | None | Redis — add after measurements show a hot path |
| Orchestration | Docker Compose | Kubernetes — not justified for one machine |
| Python tooling | `uv`, `ruff`, `mypy`, `pytest` | — (decision D6) |
