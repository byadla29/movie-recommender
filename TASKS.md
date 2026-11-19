# TASKS

Current phase: **Phase 1 — Foundation (complete, awaiting review)**
Next step: **Owner reviews Phase 1. Then propose the Phase 2 plan (Clerk sign-in, preferences API, onboarding).**

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
- [ ] CI run on GitHub: not yet executed (no remote configured, nothing committed yet)

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
- [ ] IdP (Clerk) integration + protected routes
- [ ] JWT validation per service; ownership tests
- [ ] Preferences, consents, account deletion (user-service)
- [ ] Onboarding wizard + settings pages

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

## Blockers / needs from owner
- Review Phase 1; decide whether to commit and push to a GitHub remote so CI can run.
- Phase 2: a Clerk account + development instance keys (publishable + secret) in `frontend/.env.local`.
- Phase 3: TMDB API key (fixtures work without it).

## Known issues / risks
- Vitest fails on Windows when the shell cwd has a lowercase drive letter (`c:\`); run from `C:\` (see README).
- Starlette warns that `httpx` in TestClient is deprecated in favour of `httpx2`; harmless for now.
- 14 "high" npm audit findings are in dev-only dependencies; production deps report 0.
- GitHub Action versions in CI are pinned to major tags, not commit SHAs (tighten in Phase 6).
