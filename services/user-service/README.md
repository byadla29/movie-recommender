# user-service

Owns profiles, country/region, language and genre preferences, consents and watchlists
(see `docs/architecture.md`). Phase 1: operational skeleton only.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness: process is up (no dependencies checked) |
| `GET /ready` | Readiness: database reachable and migrations at head |
| `GET /docs` | Swagger UI (local only) |

## Develop (outside Docker)

```bash
cd services/user-service
uv sync                                   # create .venv with runtime + dev deps
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest                             # unit tests (integration tests skip)

# against the Compose Postgres (docker compose up -d postgres):
cp .env.example .env                      # then set the real user_svc password
uv run alembic upgrade head
uv run uvicorn user_service.main:create_app --factory --reload --port 8001
RUN_INTEGRATION=1 uv run pytest tests/integration
```

## Layout

```
src/user_service/
  api/            HTTP routes (thin)
  readiness.py    readiness logic (pure, testable)
  request_context.py, logging_config.py, errors.py, settings.py, db.py
migrations/       Alembic (this service's database only)
tests/unit, tests/integration
```
