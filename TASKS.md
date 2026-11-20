# TASKS

Current phase: **Phase 2 — Identity & onboarding (in progress on branch `phase-2`)**
Next step: **2.9 — settings page (edit, consent, delete account) + Phase 2 docs and acceptance checks.**

## Phase 0 — Design (done)
- [x] Inspect repository (only `CLAUDE.md` present; not yet a git repo)
- [x] `docs/requirements.md` — functional/non-functional requirements, journeys, MVP acceptance
- [x] `docs/architecture.md` — components, data ownership, failure modes
- [x] `docs/service-communication.md` — call map, timeouts/retries, sequences, broker gate
- [x] `docs/dataset-strategy.md` — MovieLens, TMDB, Wikidata, IMDb, fixtures; proxy labeling
- [x] `docs/database-design.md` — per-service schemas, isolation, deletion paths
- [x] `docs/api-contracts.md` — v1 endpoints and examples
- [x] `docs/frontend-design.md` — pages, components, tracking, a11y, tests
- [x] `docs/recommendation-design.md` — math, worked examples, evaluation, test list
- [x] `docs/implementation-plan.md` — structure, phases, timeline, decisions, risks
- [x] `docs/adr/0001-service-boundaries.md`
- [x] Owner approval of architecture + decisions D1–D8 (2026-11-18)

## Phase 1 — Foundation (done 2026-11-18)
- [x] `git init` (branch `main`), `.gitignore`, `.gitattributes` (LF), root README, `.env.example` files
- [x] Postgres init script: 3 databases + 3 roles, CONNECT revoked from PUBLIC
- [x] user-service skeleton (`/health`, `/ready`, JSON logs, request ID, problem+json, Alembic baseline)
- [x] catalog-service skeleton (same)
- [x] recommendation-service skeleton (same)
- [x] Next.js 16 skeleton (TS, Tailwind, ESLint, Vitest): landing page + `/status` BFF readiness page
- [x] `docker-compose.yml` with healthchecks; frontend degrades when a service is down
- [x] OpenAPI export script (`scripts/export-openapi.sh`, `--check` for CI) → `contracts/openapi/`
- [x] CI workflow (lint, type-check, unit + integration tests, contract drift, frontend, docker build)
- [x] First commit pushed to GitHub (`byadla29/movie-recommender`, `main`)

### Verified locally (2026-11-18)
| Check | Result |
|---|---|
| ruff check + format, mypy --strict (×3 services) | clean |
| pytest unit (×3) | 14 passed each |
| pytest integration vs Compose Postgres (×3) | 5 passed each (incl. role cannot connect to other DBs) |
| frontend lint, `tsc`, Vitest, `next build` | clean, 7 tests passed, build OK |
| `docker compose up --build` | 5/5 containers healthy; `/ready` = database ok, migrations ok |
| recommendation-service stopped | `/status` still 200, shows "Unreachable" |
| OpenAPI `--check` | no drift |

## Phase 2 — Identity & onboarding
Approved 2026-11-19 as 9 small steps, one commit each, on branch `phase-2`; merged to `main`
via one pull request at the end. Each step stops for owner review before committing.

Backend (no Clerk account needed):
- [x] 2.1 Vocabularies `contracts/vocab/{languages,genres,regions}.v1.json` + `scripts/check_vocab.py` + CI step
- [x] 2.2 user-service tables: users, preferences, languages, genres, consents (Alembic 0002)
- [x] 2.3 user-service token validation (JWT via JWKS; 401 on missing/expired/tampered)
- [x] 2.4 Preferences API `GET/PUT /v1/me/preferences` + ownership tests + contract update
- [x] 2.5 Consents API + `DELETE /v1/me`

Frontend (needs Clerk development keys in `frontend/.env.local`):
- [x] 2.6 Clerk sign-in/up/out + protected routes
- [x] 2.7 BFF client for user-service (forwards token, timeouts) + `/home` placeholder
- [x] 2.8 Onboarding form (region → languages → genres → consent; one page, four sections)
- [ ] 2.9 Settings page (edit, consent, delete account) + Phase 2 docs and acceptance checks

### Verified (Phase 2)
| Step | Check | Result |
|---|---|---|
| 2.1 | `python scripts/check_vocab.py` | OK, 3 files valid (exit 0) |
| 2.1 | checker on deliberately broken copies (duplicate, unsorted, bad slug, region under wrong country) | 4 errors reported (exit 1) |
| 2.1 | ruff check/format + `mypy --strict` on `scripts/check_vocab.py` | clean |
| 2.2 | user-service ruff check/format, mypy (src, strict) | clean |
| 2.2 | user-service unit tests | 18 passed (4 new model tests) |
| 2.2 | user-service integration tests vs Compose Postgres | 18 passed: models = migrations, downgrade/upgrade round trip, cascade delete, 7 invalid rows rejected, unique rank, unique `user_sub` (all in rolled-back transactions) |
| 2.2 | old container vs migrated DB → rebuilt container | `/ready` 503 "at 0002, expected 0001" → 200 ready |
| 2.2 | OpenAPI `--check` | no drift (no API change in this step) |
| 2.3 | user-service ruff check/format, mypy (src, strict) | clean |
| 2.3 | user-service unit tests | 55 passed (37 new auth tests: 12 bad-token kinds × verifier + HTTP, audience/azp, 503 cases, local JWKS server, no token in logs) |
| 2.3 | each bad token rejected for the intended reason (printed) | DecodeError, InvalidSignature ×2, InvalidAlgorithm ×2, Expired, Immature, InvalidIssuer, MissingClaim ×2, empty sub, oversized |
| 2.3 | OpenAPI `--check` | no drift (no route uses auth yet; first in 2.4) |
| 2.3 | `docker compose up -d --build --wait` | 5/5 healthy; user-service `/ready` ok; image has pyjwt 2.15.1, cryptography 50.0.2 |
| 2.4 | user-service ruff check/format, mypy (src, strict) | clean |
| 2.4 | user-service unit tests | 78 passed (23 new: domain rules, 401s, 422 shape + vocabulary errors) |
| 2.4 | user-service integration tests vs Compose Postgres | 26 passed (8 new: 404 before onboarding, PUT→GET, idempotent, replace incl. rank swap, rejected PUT changes nothing, crash mid-save rolls back, **Alice/Bob isolation**, user row from token sub) |
| 2.4 | row counts in local `user_db` after tests | 0 users / 0 preferences / 0 languages (rollback fixture works) |
| 2.4 | `scripts/sync-vocab.sh --check`, OpenAPI `--check` | no drift; contract now lists `/v1/me/preferences` with HTTPBearer, 401/404/422/503 |
| 2.4 | rebuilt container | `/ready` ok; vocab in image (22 languages); `/v1/me/preferences` → 503 "Authentication is not configured" (fail closed until 2.6) |
| 2.5 | user-service ruff check/format, mypy (src, strict) | clean |
| 2.5 | user-service unit tests | 92 passed (14 new: consent default, DB purposes = domain purposes, 401 ×3, unknown purpose, strict boolean ×4, extra fields, OpenAPI refs resolve, every `/v1/me` endpoint needs a bearer token) |
| 2.5 | user-service integration tests vs Compose Postgres | 33 passed (7 new: default off + GET creates nothing, grant→withdraw, idempotent, per-user, delete removes all of Alice's rows and none of Bob's, delete twice, delete unknown user); 0 rows left |
| 2.5 | OpenAPI contract | regenerated, no drift; shared `Problem` schema shrank file 1429 → 666 lines |
| 2.5 | rebuilt container | `/ready` ok; consents/DELETE → 503 until auth configured |
| 2.6 | frontend lint, typecheck | clean |
| 2.6 | `npm test` (Vitest) | 13 passed (6 new: proxy skips Clerk only for `/api/health`) |
| 2.6 | `next build` with real keys and with keys blanked (CI case) | both succeed; `/`, `/home`, `/sign-in`, `/sign-up`, `/status` are Partial Prerender |
| 2.6 | first Docker run without keys | **found bug**: every page 500 incl. health → container unhealthy; fixed (health skips Clerk; keys wired) |
| 2.6 | rebuilt frontend container | healthy; `/`, `/status`, `/sign-in`, `/sign-up`, `/home` 200; signed-out `/home` → `/sign-in?redirect_url=…/home` |
| 2.6 | real secret in image files | 0 files (only Clerk's own `startsWith("sk_test_")` code matches the prefix) |
| 2.7 | Clerk issuer derived from publishable key (base64 of `<host>$`) | confirmed: JWKS at `<issuer>/.well-known/jwks.json` serves 1 RSA key, `alg=RS256` |
| 2.7 | user-service with `AUTH_ISSUER` + `azp` allow-list | no token → 401, forged token → 401 (was 503 before configuring) |
| 2.7 | frontend lint, typecheck, `next build` (keys blanked) | clean |
| 2.7 | `npm test` (Vitest) | 36 passed (23 new: client headers/timeout/status mapping/bounded retry/no token in results; summary states) |
| 2.7 | **end to end** (owner signed in, opened `/home`) | page: "You haven't chosen…"; user-service logs: `GET /v1/me/preferences` → 404, no 401 → real Clerk token accepted (iss, azp, RS256, exp); 0 rows created; 0 tokens in logs |
| 2.8 | frontend lint, typecheck, `next build` (keys blanked), `sync-vocab.sh --check` | clean; `/onboarding` is Partial Prerender |
| 2.8 | `npm test` (Vitest) | 63 passed (27 new: vocab labels, form parsing/checks/server-error mapping/prefill, Server Action decisions incl. consent failure, form a11y labels, tracking off by default, errors keep choices) |
| 2.8 | **end to end, flow A** (owner): `/home` → redirected to `/onboarding` → saved → `/home` shows names | user-service: GET prefs 404 ×2, GET consents 200, PUT prefs 200, PUT consent 200, GET prefs 200; DB: 1 user, codes only (country, 2 ranked languages, 5 genres, consent); 0 tokens in logs |
| 2.8 | flow B (edit + error + re-save) | owner reported OK; logs show no second save, so the edit/re-save path is covered by automated tests only |

## Phase 3 — Catalog & UX
- [ ] Catalog schema + fixture import
- [ ] TMDB + MovieLens import CLIs (idempotent, license-noted)
- [ ] Search/details/batch-get/vocab endpoints
- [ ] Watchlist
- [ ] Search, details, watchlist pages; popular rows on homepage

## Phase 4 — Recommendations
- [ ] Feature sync + popularity jobs
- [ ] Preference matching, content similarity, hybrid ranking, MMR, language floor, explanations
- [ ] `/v1/me/home`, `/v1/movies/{id}/similar`, request logging
- [ ] Homepage rows with reasons + proxy badges; BFF fallback
- [ ] Offline evaluation CLI (MovieLens)

## Phase 5 — Interactions
- [ ] Consent-gated idempotent events endpoint + affinity updates
- [ ] Fatigue, skip suppression, exploration slots
- [ ] Frontend tracking + like/skip/simulated watch
- [ ] Simulation harness; Andhra scenario acceptance test

## Phase 6 — Quality & deployment
- [ ] Contract, E2E, a11y tests; load-test baseline; deployment; runbooks

## Phase 7 — Advanced (each gated by an ADR)
- [ ] MF/ALS, learned ranker, async pipeline, caching, vector retrieval

## Decisions log
| ID | Decision | Status |
|---|---|---|
| ADR-0001 | Three services + BFF, DB-per-service | Accepted 2026-11-18 |
| D1–D8 | See `docs/implementation-plan.md` §3 (recommended option in each row) | Approved 2026-11-18 |
| P1-a | Sync SQLAlchemy + psycopg 3 (threadpool endpoints) instead of async | Phase 1 |
| P1-b | Migrations run on container start in local Compose only (`RUN_MIGRATIONS_ON_START`) | Phase 1 |
| P1-c | Use `127.0.0.1`, not `localhost`, for published ports (Windows IPv6 hang) | Phase 1 |
| P2-a | Vocabularies are contract files validated locally by each service (not fetched from another service at runtime) | Approved 2026-11-19 |
| P2-b | DB CHECKs validate code format; vocabulary membership is checked in application code. No `display_name`/`deleted_at` columns (data minimisation; hard delete + cascade) | Step 2.2 |
| P2-c | Integration tests run inside rolled-back transactions so they never change local data | Step 2.2 |
| P2-d | PyJWT (+cryptography) verifies tokens locally via JWKS; RS256 only; 401 generic message; JWKS unreachable or auth unconfigured → 503 (fail closed) | Step 2.3 |
| P2-e | Services get vocab as build-time copies (`scripts/sync-vocab.sh`, CI `--check`), because each Docker build only sees its own folder | Step 2.4 |
| P2-f | Layering `api` (HTTP/Pydantic) → `domain` (pure rules) → `repositories` (SQL); write routes commit explicitly before responding | Step 2.4 |
| P2-g | Consent: no row = not granted; strict booleans; latest answer only (no history yet). Deletion: per-service idempotent `DELETE /v1/me`, BFF orchestrates, identity deleted last | Step 2.5 |
| P2-h | Clerk `@clerk/nextjs` 7.x; `proxy.ts` runs `clerkMiddleware()` (no route rules there; `createRouteMatcher` is deprecated); pages gate with `auth.protect()` inside `<Suspense>`; `/api/health` bypasses Clerk | Step 2.6 |
| P2-i | Publishable key = Docker build arg (public, baked into JS); secret key = runtime-only `env_file` from `frontend/.env.local` | Step 2.6 |
| P2-j | BFF→user-service: pure client (token + URL as inputs) + `server-only` wrapper getting the Clerk token; typed results; 1500 ms timeout; 1 retry for reads on "unavailable" only | Step 2.7 |
| P2-k | Onboarding = one page, four fieldsets, real `<form>` + Server Action (works without JS); 5 ordered language slots; quick checks in the BFF, user-service authoritative; preferences then consent as two idempotent PUTs; idempotent PUTs retried once; `/home` redirects to `/onboarding` on 404; frontend gets vocab copies via `sync-vocab.sh` | Step 2.8 |

## Blockers / needs from owner
- Phase 3: TMDB API key (fixtures work without it).

## Known issues / risks
- Vitest fails on Windows when the shell cwd has a lowercase drive letter (`c:\`); run from `C:\` (see README).
- Signed-out request to a protected page returns HTTP 200 with a streamed redirect (Clerk +
  Cache Components trade-off); no protected content is rendered. Data is protected by the
  services' token checks regardless.
- Starlette warns that `httpx` in TestClient is deprecated in favour of `httpx2`; harmless for now.
- 14 "high" npm audit findings are in dev-only dependencies; production deps report 0.
- GitHub Action versions in CI are pinned to major tags, not commit SHAs (tighten in Phase 6).
- mypy checks only `src/`; tests and migrations are not type-checked (would need a `py.typed`
  marker and config change). Candidate small improvement.
