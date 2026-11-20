# TASKS

Current phase: **Phase 2 — Identity & onboarding (in progress on branch `phase-2`)**
Next step: **2.3 — user-service token validation (JWT via JWKS).**

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
- [ ] 2.3 user-service token validation (JWT via JWKS; 401 on missing/expired/tampered)
- [ ] 2.4 Preferences API `GET/PUT /v1/me/preferences` + ownership tests + contract update
- [ ] 2.5 Consents API + `DELETE /v1/me`

Frontend (needs Clerk development keys in `frontend/.env.local`):
- [ ] 2.6 Clerk sign-in/up/out + protected routes
- [ ] 2.7 BFF client for user-service (forwards token, timeouts) + `/home` placeholder
- [ ] 2.8 Onboarding wizard (region → languages → genres → consent)
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

## Blockers / needs from owner
- Phase 2: a Clerk account + development instance keys (publishable + secret) in `frontend/.env.local`.
- Phase 3: TMDB API key (fixtures work without it).

## Known issues / risks
- Vitest fails on Windows when the shell cwd has a lowercase drive letter (`c:\`); run from `C:\` (see README).
- Starlette warns that `httpx` in TestClient is deprecated in favour of `httpx2`; harmless for now.
- 14 "high" npm audit findings are in dev-only dependencies; production deps report 0.
- GitHub Action versions in CI are pinned to major tags, not commit SHAs (tighten in Phase 6).
- mypy checks only `src/`; tests and migrations are not type-checked (would need a `py.typed`
  marker and config change). Candidate small improvement.
