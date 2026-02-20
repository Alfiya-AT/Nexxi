"""
app/middleware/rate_limiter.py

Per-API-key rate limiting using slowapi (Starlette-compatible).

Design Decisions:
- slowapi is a thin wrapper around the limits library, backed by
  Redis for distributed rate limiting across multiple workers.
- Rate limit is applied per X-API-Key header, not per IP, to avoid
  penalising users behind shared NAT.
- The limiter instance is a module-level singleton so FastAPI routes
  can import it for the @limiter.limit() decorator.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def _get_api_key(request: Request) -> str:
    """
    Key function for rate limiting: use X-API-Key if present,
    fall back to client IP address.
    """
    return request.headers.get("X-API-Key") or get_remote_address(request)


# Module-level singleton — imported by routes and main.py
limiter = Limiter(
    key_func=_get_api_key,
    default_limits=["60/minute"],
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379"),
)
