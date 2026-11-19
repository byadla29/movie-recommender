import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from reco_service.request_context import resolve_request_id


def test_generates_request_id_when_missing(client: TestClient) -> None:
    response = client.get("/health")

    assert len(response.headers["X-Request-ID"]) == 32  # uuid4 hex


def test_reuses_well_formed_incoming_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "bff-req-123"})

    assert response.headers["X-Request-ID"] == "bff-req-123"


@pytest.mark.parametrize("unsafe", ["has space", "x" * 65, 'inject"}', "line\nbreak", ""])
def test_rejects_unsafe_incoming_request_ids(unsafe: str) -> None:
    assert resolve_request_id(unsafe) != unsafe


def test_unknown_route_returns_problem_json(client: TestClient) -> None:
    response = client.get("/does-not-exist", headers={"X-Request-ID": "trace-404"})

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "/does-not-exist",
        "request_id": "trace-404",
    }


def test_unhandled_exception_returns_generic_500(app: FastAPI, client: TestClient) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    response = client.get("/boom", headers={"X-Request-ID": "trace-500"})

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    assert "secret" not in response.text
    assert body["request_id"] == "trace-500"
    assert response.headers["X-Request-ID"] == "trace-500"


def test_validation_error_does_not_echo_input(app: FastAPI, client: TestClient) -> None:
    @app.get("/items")
    def items(limit: int) -> dict[str, int]:
        return {"limit": limit}

    response = client.get("/items", params={"limit": "not-a-number-SENSITIVE"})

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "https://errors.movie-reco.local/validation"
    assert body["errors"][0]["loc"] == ["query", "limit"]
    assert "SENSITIVE" not in response.text
