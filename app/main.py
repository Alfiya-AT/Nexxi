"""
app/main.py

FastAPI application entry point for Nexxi.

Startup sequence:
  1. Load environment variables from .env
  2. Configure structured logging
  3. Connect to Redis
  4. Load the Hugging Face model (singleton)
  5. Wire up services (ChatService, SafetyFilter, etc.)
  6. Register middleware (auth, rate limiting, logging, CORS)
  7. Mount routers
  8. Expose Prometheus metrics endpoint

Shutdown sequence:
  1. Unload model and release VRAM
  2. Close Redis connection

Design Decisions:
- asynccontextmanager lifespan is used (modern FastAPI ≥0.93)
  instead of deprecated @app.on_event handlers.
- All service instances are attached to app.state so routes can
  access them via FastAPI's Depends pattern — no global singletons
  in service layers (easier to test).
- CORS origins are loaded from config (not hardcoded) so they can
  differ per environment.
- The /metrics endpoint is exposed by prometheus-fastapi-instrumentator
  and does NOT require API key auth (added to OPEN_PATHS in auth.py).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv

# Load .env BEFORE importing anything that reads env vars
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.middleware.auth import APIKeyMiddleware
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limiter import limiter
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.schemas.chat_schema import ErrorResponse
from app.services.chat_service import ChatService
from app.services.conversation_manager import ConversationManager, create_redis_client
from app.services.model_loader import load_model, unload_model
from app.services.safety_filter import SafetyFilter
from app.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


# ── Application lifespan ───────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and graceful shutdown.

    Startup:
        - Connect to Redis
        - Load HF model
        - Wire up services

    Shutdown:
        - Release model VRAM
        - Close Redis connection
    """
    logger.info("🚀 Nexxi starting up...")

    # ── Redis ──────────────────────────────────────────────────
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_client = await create_redis_client(redis_url)
    app.state.redis = redis_client

    # ── Model ──────────────────────────────────────────────────
    model_name = os.environ.get("HF_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.3")
    load_model(
        model_name=model_name,
        device="auto",
        quantization=os.environ.get("MODEL_QUANTIZATION", "4bit"),
    )

    # ── Services ───────────────────────────────────────────────
    conversation_manager = ConversationManager(
        redis_client=redis_client,
        max_history_turns=int(os.environ.get("MAX_HISTORY_TURNS", "10")),
        session_ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", "1800")),
    )

    safety_filter = SafetyFilter(
        max_input_length=int(os.environ.get("MAX_INPUT_LENGTH", "1000")),
        enable_ml_moderation=os.environ.get("ENABLE_ML_MODERATION", "false").lower() == "true",
    )

    chat_service = ChatService(
        conversation_manager=conversation_manager,
        safety_filter=safety_filter,
        max_new_tokens=int(os.environ.get("MAX_NEW_TOKENS", "512")),
    )

    # Attach services to app.state so routes can access via Depends
    app.state.chat_service = chat_service
    app.state.conversation_manager = conversation_manager

    logger.info("✅ Nexxi is ready to serve requests")

    yield  # Application runs here

    # ── Graceful shutdown ──────────────────────────────────────
    logger.info("🛑 Nexxi shutting down...")
    unload_model()
    await redis_client.aclose()
    logger.info("Shutdown complete")


# ── FastAPI app factory ────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory pattern makes the app importable for testing
    without triggering startup side effects.
    """
    app_env = os.environ.get("APP_ENV", "development")

    app = FastAPI(
        title="Nexxi API",
        description=(
            "**Nexxi** — Next-gen AI chatbot powered by Hugging Face.\n\n"
            "_Next-gen answers, right now._\n\n"
            "All endpoints (except `/health`, `/ready`, `/metrics`) require "
            "an `X-API-Key` header."
        ),
        version="1.0.0",
        docs_url="/docs" if app_env != "production" else None,
        redoc_url="/redoc" if app_env != "production" else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (applied in reverse order — last added = first executed) ──

    # 1. Request/response logging (outermost — logs every request)
    app.add_middleware(RequestLoggingMiddleware)

    # 2. API Key authentication
    app.add_middleware(APIKeyMiddleware)

    # 3. CORS
    cors_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    )

    # ── Rate limiter exception handler ─────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Custom exception handlers ──────────────────────────────
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="NOT_FOUND",
                detail=f"The path '{request.url.path}' was not found.",
            ).model_dump(mode="json"),
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="INTERNAL_SERVER_ERROR",
                detail="An unexpected error occurred. Please try again.",
            ).model_dump(mode="json"),
        )

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(chat_router)

    # ── Prometheus metrics ─────────────────────────────────────
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/health", "/ready"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    logger.info("FastAPI application created", env=app_env)
    return app


# ── Application instance ───────────────────────────────────────
# Imported by uvicorn: uvicorn app.main:app
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("APP_ENV", "development") == "development",
        workers=1,  # Single worker for shared model memory
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
