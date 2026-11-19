"""Operational endpoints: liveness and readiness. Unversioned, unauthenticated."""

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from reco_service.db import get_engine
from reco_service.errors import PROBLEM_JSON, problem_response
from reco_service.readiness import ReadinessResult, check_readiness, expected_migration_head
from reco_service.settings import get_settings

router = APIRouter(tags=["operations"])

ReadinessProbe = Callable[[], ReadinessResult]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    checks: dict[str, str]


def get_readiness_probe() -> ReadinessProbe:
    """Dependency so tests can swap in a fake probe without a database."""
    settings = get_settings()
    return lambda: check_readiness(get_engine(), expected_migration_head(settings.alembic_ini_path))


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().service_name)


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness check (database reachable, migrations at head)",
    responses={503: {"description": "Not ready", "content": {PROBLEM_JSON: {}}}},
)
def ready(
    request: Request, probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)]
) -> ReadyResponse | JSONResponse:
    result = probe()
    if not result.ready:
        return problem_response(
            request, 503, detail="Service not ready", extra={"checks": result.checks}
        )
    return ReadyResponse(status="ready", checks=result.checks)
