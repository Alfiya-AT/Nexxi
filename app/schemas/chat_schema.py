"""
app/schemas/chat_schema.py

Pydantic v2 request/response schemas for Nexxi's chat API.

Design Decisions:
- Field validators enforce business rules at the schema layer so
  service code doesn't need to repeat them.
- `session_id` is optional on request — if absent, the route layer
  generates one.  This improves DX for stateless/first-message use.
- `model` in the response returns only the short model label, NOT
  the full Hugging Face repo path (prevents internal leak).
- `ErrorResponse` mirrors RFC 7807 Problem Details for alignment
  with standard API error conventions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Request schemas ────────────────────────────────────────────

class ChatRequest(BaseModel):
    """
    Payload for POST /v1/chat and POST /v1/chat/stream.

    Fields:
        session_id: Optional conversation session identifier.
                    If not provided, a new session will be created.
        message: The user's message (1–1000 characters).
        stream: If True, use Server-Sent Events streaming response.
    """

    session_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Conversation session ID. Omit to start a new session.",
            examples=["550e8400-e29b-41d4-a716-446655440000"],
        ),
    ] = None

    message: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=1000,
            description="The user's message to Nexxi (max 1000 characters).",
            examples=["What is quantum computing?"],
        ),
    ]

    stream: Annotated[
        bool,
        Field(
            default=False,
            description="Enable streaming (SSE) response.",
        ),
    ] = False

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, v: str) -> str:
        """Strip leading/trailing whitespace from the message."""
        return v.strip()

    @field_validator("session_id", mode="before")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """Ensure session_id, if provided, looks like a UUID."""
        if v is None:
            return None
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError("session_id must be a valid UUID v4 string.")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is quantum computing?",
                    "stream": False,
                },
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "message": "Can you elaborate on that?",
                    "stream": True,
                },
            ]
        }
    }


class DeleteSessionRequest(BaseModel):
    """Payload for DELETE /v1/chat/session."""

    session_id: Annotated[
        str,
        Field(
            ...,
            description="The session ID to delete.",
            examples=["550e8400-e29b-41d4-a716-446655440000"],
        ),
    ]


# ── Response schemas ───────────────────────────────────────────

class ChatResponse(BaseModel):
    """
    Successful response from POST /v1/chat.

    Fields:
        session_id: Session identifier (new or existing).
        message: Nexxi's generated response.
        model: Short model label (never the full HF repo path).
        tokens_used: Approximate output token count.
        response_time_ms: End-to-end latency in milliseconds.
        timestamp: UTC timestamp of the response.
    """

    session_id: Annotated[
        str,
        Field(description="Session identifier."),
    ]

    message: Annotated[
        str,
        Field(description="Nexxi's response to the user's message."),
    ]

    model: Annotated[
        str,
        Field(
            description="Model label used to generate the response.",
            examples=["Mistral-7B-Instruct-v0.3"],
        ),
    ]

    tokens_used: Annotated[
        int,
        Field(
            ge=0,
            description="Approximate number of output tokens generated.",
        ),
    ]

    response_time_ms: Annotated[
        float,
        Field(
            ge=0.0,
            description="End-to-end request processing time in milliseconds.",
        ),
    ]

    timestamp: Annotated[
        datetime,
        Field(
            default_factory=lambda: datetime.now(timezone.utc),
            description="UTC timestamp when the response was generated.",
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "message": "Quantum computing harnesses quantum mechanics to process information...",
                    "model": "Mistral-7B-Instruct-v0.3",
                    "tokens_used": 128,
                    "response_time_ms": 1240.5,
                    "timestamp": "2025-01-01T12:00:00Z",
                }
            ]
        }
    }


class StreamChunk(BaseModel):
    """
    A single chunk in a Server-Sent Events streaming response.

    Fields:
        session_id: Session identifier.
        delta: Partial text token(s) to append to the response.
        finished: True on the final chunk.
        error: Non-null only on error chunks.
    """

    session_id: str
    delta: str = ""
    finished: bool = False
    error: str | None = None


class DeleteSessionResponse(BaseModel):
    """Response for DELETE /v1/chat/session."""

    message: str = "Session deleted successfully."
    session_id: str


# ── Health schemas ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response for GET /health (liveness check)."""

    status: str = "ok"
    service: str = "Nexxi"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ReadinessResponse(BaseModel):
    """Response for GET /ready (readiness check — all dependencies healthy)."""

    status: str          # "ready" | "not_ready"
    model_loaded: bool
    redis_connected: bool
    details: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ── Error schema ───────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """
    RFC 7807-aligned error response for all 4xx/5xx responses.

    Fields:
        error: Machine-readable error code (e.g. 'RATE_LIMIT_EXCEEDED').
        detail: Human-readable explanation safe to surface to the client.
        timestamp: UTC timestamp of the error.
    """

    error: Annotated[
        str,
        Field(description="Machine-readable error code."),
    ]

    detail: Annotated[
        str,
        Field(description="Human-readable error explanation."),
    ]

    timestamp: Annotated[
        datetime,
        Field(
            default_factory=lambda: datetime.now(timezone.utc),
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "RATE_LIMIT_EXCEEDED",
                    "detail": "You have exceeded the 60 requests/minute limit.",
                    "timestamp": "2025-01-01T12:00:00Z",
                }
            ]
        }
    }
