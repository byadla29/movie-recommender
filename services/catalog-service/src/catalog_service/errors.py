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
from starlette.exceptions import HTTPException as StarletteHTTPException

from catalog_service.request_context import REQUEST_ID_HEADER, request_id_var

PROBLEM_JSON = "application/problem+json"
logger = logging.getLogger(__name__)


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
        type_="https://errors.movie-reco.local/validation",
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
    app.add_exception_handler(Exception, _unhandled_exception_handler)
