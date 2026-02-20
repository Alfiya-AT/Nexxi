"""
app/routes/health.py

Health and readiness check endpoints.

GET /health  → Liveness probe — is the process running?
GET /ready   → Readiness probe — are all dependencies healthy?

Design Decisions:
- Health (liveness) is a cheap check that returns 200 as long as
  the process is alive. Kubernetes uses this to decide if it should
  restart the pod.
- Readiness goes deeper: it verifies the model is loaded and Redis
  is reachable. Kubernetes uses this to determine if traffic should
  be routed to the pod.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.chat_schema import HealthResponse, ReadinessResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Check",
    description="Returns 200 if the Nexxi service process is running.",
)
async def health_check() -> HealthResponse:
    """Kubernetes liveness probe endpoint."""
    return HealthResponse(status="ok", service="Nexxi")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Check",
    description=(
        "Returns 200 if the model is loaded and all dependencies are healthy. "
        "Returns 503 if any dependency is unavailable."
    ),
)
async def readiness_check() -> JSONResponse:
    """Kubernetes readiness probe endpoint."""
    from app.services import model_loader

    checks: dict[str, str] = {}
    model_ok = False
    redis_ok = False

    # ── Model check ───────────────────────────────────────────
    try:
        model_loader.get_model()
        model_ok = True
        checks["model"] = "loaded"
    except Exception as exc:
        checks["model"] = f"not loaded: {exc}"
        logger.warning("Readiness: model not loaded")

    # ── Redis check ───────────────────────────────────────────
    try:
        # Access the application state redis client
        import redis.asyncio as aioredis
        import os

        client = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379"),
            socket_connect_timeout=2,
        )
        await client.ping()
        await client.aclose()
        redis_ok = True
        checks["redis"] = "connected"
    except Exception as exc:
        checks["redis"] = f"unreachable: {exc}"
        logger.warning("Readiness: Redis unreachable")

    all_ready = model_ok and redis_ok
    status_code = 200 if all_ready else 503

    return JSONResponse(
        status_code=status_code,
        content=ReadinessResponse(
            status="ready" if all_ready else "not_ready",
            model_loaded=model_ok,
            redis_connected=redis_ok,
            details=checks,
        ).model_dump(mode="json"),
    )
