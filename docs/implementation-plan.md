# Implementation Plan

Status: **Approved 2026-11-18; Phases 1–2 complete** · Last updated: 2026-11-20

## 1. Proposed repository structure (built up phase by phase — not created up front)

```
movie-recommender/
├─ CLAUDE.md  TASKS.md  README.md  .gitignore  .env.example  docker-compose.yml
├─ .github/workflows/ci.yml
├─ contracts/
│  ├─ openapi/{user,catalog,recommendation}-service.v1.json   (generated, committed)
│  ├─ vocab/genres.v1.json  languages.v1.json  regions.v1.json  (checked by scripts/check_vocab.py)
│  └─ events/            (Phase 7, only if a broker is adopted)
├─ data/
│  ├─ fixtures/          fictional movies + synthetic users (committed, ours)
│  ├─ scripts/           download + checksum helpers
│  └─ raw/               git-ignored (MovieLens, TMDB dumps)
├─ docs/  (this folder) + adr/
├─ frontend/             Next.js app (UI + BFF)
├─ infra/postgres/init/  creates 3 databases + 3 roles
└─ services/
   ├─ user-service/
   ├─ catalog-service/
   └─ recommendation-service/
       ├─ pyproject.toml  Dockerfile  .env.example  alembic.ini
       ├─ migrations/
       ├─ src/reco_service/
       │  ├─ api/          routes + Pydantic schemas (thin)
       │  ├─ domain/       pure algorithms: popularity, affinity, content, ranking, explain
       │  ├─ repositories/ SQLAlchemy data access
       │  ├─ clients/      HTTP clients to other services (timeouts/retries)
       │  ├─ jobs/         CLI: sync-features, compute-popularity, evaluate
       │  └─ settings.py  auth.py  main.py
       └─ tests/ unit/ integration/
```

Every service follows the same layout (`api → domain ← repositories`), so business logic
is testable without HTTP or a database.

## 2. Phases

Timeline assumes **~10–15 hours/week**, solo, learning as we go. Weeks are rough estimates.

### Phase 0 — Design (this phase) · ~1 week incl. your review
- **Deliverables:** all `docs/*`, ADR 0001, `TASKS.md`.
- **Acceptance:** you approve architecture and decisions D1–D8 (§3).

### Phase 1 — Foundation · ~2 weeks · depends on Phase 0
- `git init`, `.gitignore`, `.env.example` files, README.
- Three FastAPI skeletons with `/health`, `/ready`, settings, JSON logging, request-ID middleware, problem+json errors.
- Postgres container with init script creating 3 DBs + 3 roles; an empty Alembic baseline per service.
- Next.js app skeleton (TS, Tailwind, ESLint) with a landing page.
- `docker-compose.yml` with healthchecks; OpenAPI export script; CI (ruff, mypy, pytest, tsc, eslint, vitest, docker build).
- **Acceptance:** `docker compose up` → all 4 apps healthy; `/ready` proves DB connectivity;
  a test proves `user_svc` cannot connect to `catalog_db`; CI green.

### Phase 2 — Identity & onboarding · ~2 weeks · depends on Phase 1, D1
- IdP integration in Next.js (sign up/in/out, middleware protection).
- Shared JWT-validation module *per service* (copied pattern, not a shared package — D7).
- user-service: preferences, consents, `DELETE /v1/me`; vocab validation.
- Onboarding wizard + settings pages.
- **Acceptance:** unauthenticated API calls → 401; tampered/expired token → 401; user A
  cannot read user B's data (test); onboarding persists and redirects to `/home` placeholder.

### Phase 3 — Catalog & UX · ~3 weeks · depends on Phase 2, D2
- catalog schema, fixture import, TMDB import CLI (bounded), MovieLens links/aggregates import.
- Search (FTS + trigram), details, batch-get, genres/languages endpoints.
- Watchlist in user-service (validates movie via catalog).
- Frontend: search page, details page, watchlist page, homepage with *catalog-popularity* rows.
- **Acceptance:** re-running imports creates no duplicates; search p95 measured on 5k+ movies;
  pagination tested; attribution visible; licenses recorded in `import_runs`.

### Phase 4 — Recommendations · ~3 weeks · depends on Phase 3
- recommendation-service: feature sync job, popularity job (global/language/country-proxy),
  preference matching, content vectors + `/similar`, hybrid ranking (c = 0 path), MMR,
  language floor, explanations, `/v1/me/home`, request/item logging.
- Frontend rows with reasons and proxy badges; BFF fallback on reco failure.
- Offline evaluation CLI on MovieLens (popularity vs content vs hybrid).
- **Acceptance:** unit tests in `recommendation-design.md` §8 pass; homepage shows ≥4
  labeled rows for a new user; stopping reco container still renders popular rows;
  evaluation report generated with stated limitations.

### Phase 5 — Interactions · ~3 weeks · depends on Phase 4
- Consent-gated events endpoint (idempotent), affinity updates, fatigue & skip suppression,
  exploration slots, deletion of events.
- Frontend impression tracker, event queue, like/skip/simulate-watch controls.
- Simulation harness with synthetic users (flagged).
- **Acceptance:** MVP criteria in `requirements.md` §7 (#4 Andhra scenario, #5 consent, #6 deletion).

### Phase 6 — Quality & deployment · ~3 weeks · depends on Phase 5
- Contract tests (OpenAPI diff + schema-based fuzzing e.g. Schemathesis), Playwright E2E,
  axe accessibility checks, OpenTelemetry tracing (optional), load-test baseline (k6 or Locust),
  deployment to one low-cost environment (decision at that time), backup/restore runbook.
- **Acceptance:** documented p50/p95 for key endpoints at stated data sizes; no critical a11y
  violations; one-command deploy with rollback notes.

### Phase 7 — Advanced learning · open-ended
- Each item requires a written justification + ADR first: implicit ALS / matrix factorization,
  learned ranker, async event pipeline (outbox + broker), Redis caching for hot rows,
  ANN/vector retrieval, scaling experiments.

**Total to end of Phase 6: ~17 weeks** at 10–15 h/week. Faster with more hours; Phase 3 and 4
are the most likely to run over (data cleaning, tuning).

## 3. Decisions (approved 2026-11-18: recommended option in each row)

| ID | Decision | Recommendation | Alternatives |
|---|---|---|---|
| **D1** | Identity provider | **Clerk** — first-class Next.js App Router SDK, hosted UI, free dev tier, standard JWTs verifiable via JWKS in FastAPI | Auth0 (similar, heavier config); Keycloak self-hosted in Compose (no vendor account, teaches OIDC deeply, more ops); Supabase Auth |
| **D2** | Metadata source | **TMDB API (non-commercial, attributed) + MovieLens for ratings/eval + fictional fixtures for tests** | Wikidata-only (CC0, but sparser); IMDb datasets (rejected: license) |
| **D3** | Cross-service user key | **IdP `sub` claim** stored as `user_sub` | Internal UUID from user-service (needs lookup/propagation) |
| **D4** | Service-to-service auth for internal endpoints | **Static per-caller token in dev → OAuth2 client-credentials later** | mTLS (overkill now) |
| **D5** | Database isolation | **One Postgres server, 3 databases, 3 roles** | 3 Postgres containers (heavier); schemas in one DB (weaker isolation) |
| **D6** | Python tooling | **uv + ruff + mypy + pytest** | Poetry/pip-tools; pyright |
| **D7** | Shared code between services | **None** — duplicate small auth/logging helpers per service; share only contracts | A shared internal Python package (less duplication, more coupling) |
| **D8** | Event processing | **Synchronous, in-transaction affinity update** in Phases 5–6; broker only via Phase 7 gate | Broker from day one (rejected: no requirement yet) |

Also please confirm:
- **Scope of initial catalog:** e.g. ~5k titles across `te, hi, ta, en` + MovieLens-linked titles.
- **Tracking consent default:** OFF until the user opts in (recommended), shown during onboarding.
- **Hours/week** you can commit, so the timeline can be adjusted.

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Regional data is a proxy | Users may over-trust "regional" rows | Visible labeling; `/about/data` page |
| Sparse Telugu metadata/ratings | Weak recs for regional languages | Language-scoped popularity; content features; honest coverage metrics per language |
| Over-engineering for one dev | Slow progress | Phase gates; no infra without justification |
| License terms change | Must remove/alter data | `import_runs.license_note`; data reproducible from scripts, not Git |
| Synthetic data mistaken for evidence | Wrong conclusions | `is_simulated` flag; reports state data provenance |
