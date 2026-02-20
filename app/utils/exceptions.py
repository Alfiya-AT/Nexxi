"""
app/utils/exceptions.py

Custom exception hierarchy for Nexxi.

Design Decisions:
- All custom exceptions inherit from NéxxiBaseError so callers
  can catch the broad class or specific subclasses.
- Each exception carries a machine-readable `error_code` that the
  HTTP layer maps to an appropriate status code.
- Sensitive fields (model name, internal paths) are never included
  in messages that bubble up to API responses.
"""

from __future__ import annotations

from typing import Any


class NéxxiBaseError(Exception):
    """Root exception for all Nexxi errors."""

    error_code: str = "NEXXI_ERROR"
    http_status: int = 500

    def __init__(self, message: str, detail: str = "", **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.extra = kwargs


# ── Model Errors ──────────────────────────────────────────────

class ModelNotLoadedError(NéxxiBaseError):
    """Raised when inference is attempted before the model is initialised."""

    error_code = "MODEL_NOT_LOADED"
    http_status = 503


class ModelLoadError(NéxxiBaseError):
    """Raised when the Hugging Face model fails to load from the hub."""

    error_code = "MODEL_LOAD_FAILED"
    http_status = 503


class InferenceError(NéxxiBaseError):
    """Raised when text generation fails during inference."""

    error_code = "INFERENCE_FAILED"
    http_status = 500


class ModelTimeoutError(NéxxiBaseError):
    """Raised when model inference exceeds the configured timeout."""

    error_code = "INFERENCE_TIMEOUT"
    http_status = 504


# ── Safety / Validation Errors ────────────────────────────────

class SafetyFilterError(NéxxiBaseError):
    """Raised when user input fails the safety / moderation check."""

    error_code = "INPUT_SAFETY_VIOLATION"
    http_status = 422


class InputTooLongError(NéxxiBaseError):
    """Raised when user input exceeds the configured character limit."""

    error_code = "INPUT_TOO_LONG"
    http_status = 400


class PromptInjectionError(NéxxiBaseError):
    """Raised when a prompt-injection or jailbreak attempt is detected."""

    error_code = "PROMPT_INJECTION_DETECTED"
    http_status = 400


# ── Session / Conversation Errors ─────────────────────────────

class SessionNotFoundError(NéxxiBaseError):
    """Raised when a session ID cannot be found in the store."""

    error_code = "SESSION_NOT_FOUND"
    http_status = 404


class SessionExpiredError(NéxxiBaseError):
    """Raised when a session has exceeded its TTL and been evicted."""

    error_code = "SESSION_EXPIRED"
    http_status = 410


class ConversationManagerError(NéxxiBaseError):
    """General error from the conversation manager (e.g. Redis failure)."""

    error_code = "CONVERSATION_MANAGER_ERROR"
    http_status = 500


# ── Auth / Rate-limit Errors ──────────────────────────────────

class AuthenticationError(NéxxiBaseError):
    """Raised when an API key is missing or invalid."""

    error_code = "AUTHENTICATION_FAILED"
    http_status = 401


class RateLimitExceededError(NéxxiBaseError):
    """Raised when a client exceeds their allowed request rate."""

    error_code = "RATE_LIMIT_EXCEEDED"
    http_status = 429


# ── Cache Errors ──────────────────────────────────────────────

class CacheError(NéxxiBaseError):
    """Raised on Redis connectivity or operation failures."""

    error_code = "CACHE_ERROR"
    http_status = 503


# ── Configuration Errors ──────────────────────────────────────

class ConfigurationError(NéxxiBaseError):
    """Raised when required configuration or environment variables are missing."""

    error_code = "CONFIGURATION_ERROR"
    http_status = 500
