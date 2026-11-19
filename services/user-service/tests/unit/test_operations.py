from fastapi import FastAPI
from fastapi.testclient import TestClient

from user_service.api.health import get_readiness_probe
from user_service.readiness import ReadinessResult


def test_health_returns_ok_without_touching_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "user-service"}


def test_ready_returns_200_when_all_checks_pass(app: FastAPI, client: TestClient) -> None:
    checks = {"database": "ok", "migrations": "ok"}
    app.dependency_overrides[get_readiness_probe] = lambda: lambda: ReadinessResult(True, checks)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": checks}


def test_ready_returns_503_problem_when_a_check_fails(app: FastAPI, client: TestClient) -> None:
    checks = {"database": "ok", "migrations": "at none, expected 0001"}
    app.dependency_overrides[get_readiness_probe] = lambda: lambda: ReadinessResult(False, checks)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 503
    assert body["checks"] == checks


def test_ready_reports_unreachable_database(client: TestClient) -> None:
    # Real probe, but conftest points DATABASE_URL at a closed port.
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unreachable"}
