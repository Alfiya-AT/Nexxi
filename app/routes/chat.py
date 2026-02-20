"""
app/routes/chat.py

Chat API routes for Nexxi.

Endpoints:
  POST   /v1/chat          → Standard (non-streaming) chat
  POST   /v1/chat/stream   → Streaming chat via Server-Sent Events
  DELETE /v1/chat/session  → Clear a session's conversation history

Design Decisions:
- ChatService is injected via FastAPI's Depends pattern for
  clean testability and separation of concerns.
- Streaming uses StreamingResponse with text/event-stream MIME type
  conforming to the SSE spec.
- All error responses use the ErrorResponse schema for consistency.
- Rate limiting is applied at the route level via slowapi decorators.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limiter import limiter
from app.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    DeleteSessionRequest,
    DeleteSessionResponse,
    ErrorResponse,
    StreamChunk,
)
from app.services.chat_service import ChatService
from app.utils.exceptions import (
    InferenceError,
    ModelNotLoadedError,
    SafetyFilterError,
    SessionNotFoundError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["Chat"])


def _get_chat_service(request: Request) -> ChatService:
    """FastAPI dependency — retrieve ChatService from app state."""
    return request.app.state.chat_service  # type: ignore[no-any-return]


def _get_or_create_session_id(request_data: ChatRequest) -> str:
    """Return the provided session_id, or generate a new UUID4."""
    if request_data.session_id:
        return request_data.session_id
    import uuid
    return str(uuid.uuid4())


# ── Standard Chat ──────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request / safety violation"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        503: {"model": ErrorResponse, "description": "Model not available"},
    },
    summary="Send a message to Nexxi",
    description=(
        "Send a message and receive Nexxi's complete response. "
        "If `session_id` is omitted, a new conversation session is created."
    ),
)
@limiter.limit("60/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    service: ChatService = Depends(_get_chat_service),
) -> ChatResponse:
    """Standard (non-streaming) chat endpoint."""
    session_id = _get_or_create_session_id(body)

    try:
        response = await service.chat(
            session_id=session_id,
            user_message=body.message,
        )
    except SafetyFilterError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except InferenceError as exc:
        logger.error(f"Inference error: {exc}")
        raise HTTPException(status_code=500, detail="Model error. Please try again.")
    except Exception as exc:
        logger.error(f"Unexpected error in /v1/chat: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    return response


# ── Streaming Chat ─────────────────────────────────────────────

@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    summary="Stream a response from Nexxi (SSE)",
    description=(
        "Stream Nexxi's response token-by-token using Server-Sent Events. "
        "Each SSE event is a JSON-encoded `StreamChunk`. "
        "The final chunk has `finished: true`."
    ),
)
@limiter.limit("60/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    service: ChatService = Depends(_get_chat_service),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint."""
    session_id = _get_or_create_session_id(body)

    async def _event_generator() -> AsyncIterator[str]:
        """Convert StreamChunk objects to SSE-formatted strings."""
        try:
            async for chunk in service.stream_chat(
                session_id=session_id,
                user_message=body.message,
            ):
                # SSE format: "data: {json}\n\n"
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as exc:
            logger.error(f"Streaming error: {exc}")
            error_chunk = StreamChunk(
                session_id=session_id,
                error="An error occurred during streaming.",
                finished=True,
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
            "Connection": "keep-alive",
        },
    )


# ── Delete Session ─────────────────────────────────────────────

@router.delete(
    "/chat/session",
    response_model=DeleteSessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
    summary="Clear a conversation session",
    description="Delete all conversation history for the given session ID.",
)
async def delete_session(
    body: DeleteSessionRequest,
    service: ChatService = Depends(_get_chat_service),
) -> DeleteSessionResponse:
    """Clear a user's conversation history."""
    try:
        await service.delete_session(body.session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{body.session_id}' not found.",
        )
    return DeleteSessionResponse(session_id=body.session_id)
