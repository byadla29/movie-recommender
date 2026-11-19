#!/bin/sh
set -eu

# Local-development convenience: apply migrations before serving. In a real deployment,
# migrations run as a separate, reviewed release step, not on every container start.
if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn reco_service.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log
