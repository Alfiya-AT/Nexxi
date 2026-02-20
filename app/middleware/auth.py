"""
app/middleware/auth.py

API key authentication middleware for Nexxi.

Design Decisions:
- API key is passed in the X-API-Key header (not query params,
  which appear in server logs).
- Keys are compared using hmac.compare_digest() to prevent
  timing attacks.
- The API key itself lives in the API_KEY environment variable —
  never in config files or code.
- Routes listed in OPEN_PATHS bypass authentication (health/metrics).
"""

from __future__ import annotations

import hmac
import os

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Paths that do not require authentication
OPEN_PATHS: frozenset[str] = frozenset({
    "/health",
    "/ready",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validates X-API-Key header on all protected endpoints.

    The expected key is loaded from the API_KEY environment variable
    at middleware instantiation time.
    """

    def __init__(self, app: object, api_key: str | None = None) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        # Load from env if not explicitly provided (e.g. in tests)
        self._expected_key = api_key or os.environ.get("API_KEY", "")
        if not self._expected_key:
            logger.warning(
                "API_KEY is not set! All authenticated endpoints will be inaccessible. "
                "Set API_KEY in your .env file."
            )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Allow open paths through without auth
        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")

        # Timing-safe comparison
        if not self._expected_key or not hmac.compare_digest(
            provided_key.encode(), self._expected_key.encode()
        ):
            logger.warning(
                "Unauthorised request",
                path=request.url.path,
                ip=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTHENTICATION_FAILED",
                    "detail": "Missing or invalid X-API-Key header.",
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                },
            )

        return await call_next(request)
