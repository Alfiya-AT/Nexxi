"""
app/middleware/logging_middleware.py

Request/response structured logging middleware.

Logs every request with:
- HTTP method and path
- Response status code
- Latency in milliseconds
- Client IP (last hop only — respects X-Forwarded-For)
- Correlation/request ID (injected into contextvars for child logs)

Design Decisions:
- Correlation ID is generated here and stored in a ContextVar so
  every log call within the same request includes the same ID.
- We intentionally do NOT log request/response bodies to prevent
  accidental PII logging. The safety filter handles PII before
  messages are persisted.
"""

from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logger import get_logger, request_id_ctx

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs structured metadata for every HTTP request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())

        # Inject into ContextVar so all downstream log calls include it
        token = request_id_ctx.set(request_id)

        start = time.monotonic()
        status_code = 500  # Default in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            logger.error(f"Unhandled exception: {exc}")
            raise
        finally:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            client_ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or (request.client.host if request.client else "unknown")
            )

            logger.info(
                "HTTP Request",
                method=request.method,
                path=request.url.path,
                status=status_code,
                latency_ms=elapsed_ms,
                ip=client_ip,
                request_id=request_id,
            )

            # Reset context var to avoid leaking across async boundaries
            request_id_ctx.reset(token)
