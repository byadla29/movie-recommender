"""Request ID propagation and one structured access-log line per request.

Concept: a *request ID* is a label attached to every log line produced while handling one
request. The BFF generates it and forwards it in `X-Request-ID`; each service reuses it, so
you can grep one ID across all services' logs to follow a single user action.

This is a pure ASGI middleware (not BaseHTTPMiddleware) so it adds no buffering and works
for streaming responses.
"""

import logging
import re
import time
import uuid
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
# Accept only short, safe IDs from callers so they can't inject newlines/JSON into logs.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("access")


def resolve_request_id(incoming: str | None) -> str:
    """Reuse a well-formed incoming ID, otherwise generate a fresh one."""
    if incoming and _SAFE_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        # Deliberately not reset afterwards: the 500 handler (which runs *outside* this
        # middleware) still needs it. Each request runs in its own task/context, and the
        # value is overwritten at the start of every request.
        request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500  # if the app crashes before responding

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],  # path only: query strings may contain user input
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
