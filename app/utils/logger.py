"""
app/utils/logger.py

Structured logging setup for Nexxi using Loguru.

Design Decisions:
- Loguru is preferred over stdlib logging for cleaner API and
  built-in structured output (JSON).
- JSON format in non-dev environments to integrate with log
  aggregators (Datadog, Loki, CloudWatch, etc.).
- PII fields are explicitly excluded from log records —
  the safety filter handles scrubbing before data reaches logs.
- Correlation IDs (request_id) are injected via context var so
  every log line within a request shares the same trace.
"""

from __future__ import annotations

import os
import sys
from contextvars import ContextVar
from typing import Any

from loguru import logger

# ── Context variable for per-request correlation ID ──────────
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def _json_serialiser(record: dict[str, Any]) -> str:
    """Custom JSON serialiser that injects the request correlation ID."""
    import json
    from datetime import datetime

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "request_id": request_id_ctx.get(""),
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    # Merge any extra key=value pairs from logger.bind(...)
    if record.get("extra"):
        payload.update(record["extra"])

    return json.dumps(payload, default=str)


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: str | None = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: 'json' for structured output, 'text' for human-readable.
        log_file: Optional file path for persistent log storage.
    """
    # Remove Loguru's default handler
    logger.remove()

    if log_format == "json":
        # Structured JSON — ideal for log aggregators
        logger.add(
            sys.stdout,
            format=_json_serialiser,  # type: ignore[arg-type]
            level=level.upper(),
            serialize=False,   # We do our own serialisation
            backtrace=False,   # Avoid leaking internal stack traces to logs
            diagnose=False,
        )
    else:
        # Human-readable text — ideal for local development
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=level.upper(),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Optionally persist to file
    if log_file:
        logger.add(
            log_file,
            rotation="100 MB",
            retention="30 days",
            compression="gz",
            level=level.upper(),
            serialize=True,  # JSON-serialised file logs
        )

    logger.info(
        "Logging initialised",
        level=level,
        format=log_format,
    )


def get_logger(name: str) -> "logger":  # type: ignore[valid-type]
    """Return a module-specific logger bound with its name."""
    return logger.bind(logger_name=name)


# ── Convenience: initialise from environment on import ───────
_level = os.getenv("LOG_LEVEL", "INFO")
_format = "text" if os.getenv("APP_ENV", "development") == "development" else "json"
setup_logging(level=_level, log_format=_format)
