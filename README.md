# Movie Discovery & Recommendation Platform

A learning project: a Netflix-style **movie discovery** app (no streaming) with personalized,
explainable recommendations, built as a small set of microservices in one monorepo.

- Design docs: [`docs/`](docs/) — start with [`architecture.md`](docs/architecture.md)
- Progress: [`TASKS.md`](TASKS.md) · Project rules: [`CLAUDE.md`](CLAUDE.md)

## Status: Phase 2 — Identity & onboarding (complete)

Three FastAPI services with health/readiness, Postgres with one isolated database per
service, and a Next.js app with sign-in (Clerk), onboarding (country/region, ordered
languages, genres, tracking consent), a settings page and account deletion. user-service
verifies Clerk tokens itself. Catalog and recommendations come next (Phases 3–4).

| Component | Local URL | Notes |
|---|---|---|
| frontend (Next.js UI + BFF) | http://127.0.0.1:3000 | `/home`, `/onboarding`, `/settings`; `/status` shows backend readiness |
| user-service | http://127.0.0.1:8001/docs | Swagger UI |
| catalog-service | http://127.0.0.1:8002/docs | Swagger UI |
| recommendation-service | http://127.0.0.1:8003/docs | Swagger UI |
| Postgres | 127.0.0.1:5433 | `user_db`, `catalog_db`, `reco_db`, one role each |

## Quick start

Prerequisites: Docker Desktop. For working outside Docker: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node 22.

```bash
cp .env.example .env          # then replace every password (URL-safe characters only)
docker compose up --build     # first run creates the 3 databases + roles
open http://127.0.0.1:3000/status
```

Reset local data (**deletes the database volume**): `docker compose down -v`.

### Sign-in (Clerk), needed from Phase 2

1. Create a free Clerk application (Email sign-in) and open **Configure → API keys**
   (Development instance).
2. Put both keys in `frontend/.env.local` (git-ignored; see `frontend/.env.example`):
   `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_…` and `CLERK_SECRET_KEY=sk_test_…`.
3. For Docker, also put the **publishable** key (public) in the root `.env` as
   `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=…`: the image build needs it. The secret key is passed
   to the running container from `frontend/.env.local` and is never built into the image.
4. In the root `.env`, set `CLERK_ISSUER_URL=https://<your-app>.clerk.accounts.dev` (public;
   the decode command is in `.env.example`). user-service verifies tokens against it.
   Without it, `/v1/me/*` endpoints answer 503 "Authentication is not configured".

Without keys the frontend still builds (CI does this), but pages return errors at runtime;
only `/api/health` keeps working.

## Checks

```bash
# each Python service (cd services/<name>)
uv sync && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
RUN_INTEGRATION=1 DATABASE_URL=postgresql+psycopg://<role>:<pw>@127.0.0.1:5433/<db> uv run pytest tests/integration

# frontend (cd frontend)
npm ci && npm run lint && npm run typecheck && npm test && npm run build

# API contracts (repo root): regenerate, or verify they match the code
bash scripts/export-openapi.sh
bash scripts/export-openapi.sh --check
```

CI (`.github/workflows/ci.yml`) runs all of the above plus a Docker image build.

## Windows notes

- Use `127.0.0.1`, not `localhost`, for the published ports: `localhost` may try IPv6 `::1`
  first and hang against Docker Desktop's IPv4-only port bindings.
- Run Vitest from a path with an **uppercase** drive letter (`C:\...`). A terminal opened at
  `c:\...` makes Vitest load modules twice and fail with "failed to find the current suite".
- If `uv` isn't on PATH after `pip install --user uv`, use `python -m uv ...`.

## Repository layout

```
contracts/openapi/   generated OpenAPI contracts (checked in CI)
docs/                requirements, architecture, data, API, DB, recommendation design, ADRs
frontend/            Next.js UI + BFF
infra/postgres/init/ creates per-service databases and roles
scripts/             developer scripts
services/            user-service, catalog-service, recommendation-service (FastAPI)
```

## Data & licensing

No datasets are included yet. See [`docs/dataset-strategy.md`](docs/dataset-strategy.md):
raw/licensed data is never committed.
