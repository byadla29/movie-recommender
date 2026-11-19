"""Readiness logic, kept separate from the HTTP route so it can be tested directly.

Concept — liveness vs readiness:
* /health (liveness): "is the process alive?" Never touches dependencies. If it fails, the
  orchestrator should restart the container.
* /ready (readiness): "can I serve real traffic?" Checks the database is reachable AND the
  schema is migrated to the latest revision. If it fails, stop sending traffic, but don't
  restart (restarting won't fix a down database).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str] = field(default_factory=dict)


def expected_migration_head(alembic_ini_path: Path) -> str | None:
    script = ScriptDirectory.from_config(Config(str(alembic_ini_path)))
    return script.get_current_head()


def check_readiness(engine: Engine, expected_head: str | None) -> ReadinessResult:
    checks: dict[str, str] = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
            current = MigrationContext.configure(conn).get_current_revision()
    except SQLAlchemyError as exc:
        # Log the exception type only: driver messages can include host/user details.
        logger.warning("readiness: database unreachable", extra={"error": type(exc).__name__})
        return ReadinessResult(ready=False, checks={"database": "unreachable"})

    if current == expected_head:
        checks["migrations"] = "ok"
    else:
        checks["migrations"] = f"at {current or 'none'}, expected {expected_head}"
    return ReadinessResult(ready=all(v == "ok" for v in checks.values()), checks=checks)
