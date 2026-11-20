"""Uniform error responses using RFC 9457 "problem details" (application/problem+json).

Every error from every service has the same shape, so the frontend handles errors one way:
    {"type": ..., "title": ..., "status": 404, "detail": ..., "instance": "/v1/...",
     "request_id": "..."}
"""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from user_service.domain.errors import DomainValidationError
from user_service.request_context import REQUEST_ID_HEADER, request_id_var

PROBLEM_JSON = "application/problem+json"
VALIDATION_TYPE = "https://errors.movie-reco.local/validation"
logger = logging.getLogger(__name__)


class Problem(BaseModel):
    """RFC 9457 problem details, as returned by every error response (for OpenAPI docs)."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str
    request_id: str | None
    # Only on 422: [{"loc": ["body", "languages", 1], "msg": "...", "type": "unknown_code"}]
    errors: list[dict[str, Any]] | None = None


PROBLEM_SCHEMA_REF = {"$ref": "#/components/schemas/Problem"}


def problem_doc(description: str) -> dict[str, Any]:
    """OpenAPI entry for one error status, e.g. responses={401: problem_doc("...")}.

    Points at ONE shared `Problem` schema instead of repeating it in every response.
    """
    return {"description": description, "content": {PROBLEM_JSON: {"schema": PROBLEM_SCHEMA_REF}}}


def register_problem_schema(app: FastAPI) -> None:
    """Add the shared `Problem` schema to the generated OpenAPI document (once)."""
    generate = app.openapi

    def openapi_with_problem() -> dict[str, Any]:
        spec = generate()  # FastAPI caches the dict it returns; we add to that same dict
        spec.setdefault("components", {}).setdefault("schemas", {})["Problem"] = (
            Problem.model_json_schema()
        )
        return spec

    app.openapi = openapi_with_problem  # type: ignore[method-assign]


def problem_response(
    request: Request,
    status: int,
    *,
    detail: str | None = None,
    type_: str = "about:blank",
    extra: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": HTTPStatus(status).phrase,
        "status": status,
        "instance": request.url.path,
        "request_id": request_id_var.get(),
    }
    if detail:
        body["detail"] = detail
    if extra:
        body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    detail = exc.detail if isinstance(exc.detail, str) else None
    return problem_response(request, exc.status_code, detail=detail, headers=exc.headers)


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Report where and why validation failed, but never echo the submitted values back.
    errors = [
        {"loc": list(err.get("loc", ())), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return problem_response(
        request,
        422,
        detail="Request validation failed",
        type_=VALIDATION_TYPE,
        extra={"errors": errors},
    )


async def _domain_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    """Business-rule failures look exactly like schema failures to the client."""
    assert isinstance(exc, DomainValidationError)
    errors = [{"loc": list(e.loc), "msg": e.msg, "type": e.type} for e in exc.errors]
    return problem_response(
        request,
        422,
        detail="Request validation failed",
        type_=VALIDATION_TYPE,
        extra={"errors": errors},
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error")
    # Runs outside RequestContextMiddleware, so add the request ID header here too.
    request_id = request_id_var.get()
    headers = {REQUEST_ID_HEADER: request_id} if request_id else None
    return problem_response(request, 500, detail="Internal server error", headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(DomainValidationError, _domain_validation_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
