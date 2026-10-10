"""Request correlation ids and access logging."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import correlation_id_var

log = logging.getLogger("sentinel.http")
_VALID_ID = re.compile(r"^[A-Za-z0-9\-_.]{8,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-correlation-id", "")
        cid = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        token = correlation_id_var.set(cid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-Id"] = cid
        log.info(
            "request",
            extra={
                "data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                    "correlation_id": cid,
                }
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response
