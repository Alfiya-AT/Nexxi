"""
tests/integration/test_chat_api.py

Integration tests for the Nexxi chat API endpoints.

Uses httpx's AsyncClient with the FastAPI app in test mode.
Model and Redis are both mocked to avoid real infrastructure dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.schemas.chat_schema import ChatResponse


TEST_API_KEY = "test-api-key-for-integration-tests"


@pytest.fixture
async def client():
    """Create a test client with mocked services."""
    with (
        patch.dict("os.environ", {"API_KEY": TEST_API_KEY, "APP_ENV": "development"}),
        patch("app.services.model_loader.load_model"),
        patch("app.services.model_loader.get_model"),
        patch("app.services.model_loader.get_tokenizer"),
        patch("app.services.model_loader.unload_model"),
        patch("app.services.conversation_manager.create_redis_client") as mock_redis_factory,
    ):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.exists = AsyncMock(return_value=False)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_redis

        from app.main import create_app
        app = create_app()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client):
        """Health endpoint should not require X-API-Key."""
        response = await client.get("/health")
        assert response.status_code != 401


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, client):
        response = await client.post("/v1/chat", json={"message": "Hello"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client):
        response = await client.post(
            "/v1/chat",
            json={"message": "Hello"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_valid_request_accepted(self, client):
        """A valid request with correct API key should not return 4xx auth errors."""
        with patch(
            "app.services.chat_service.ChatService.chat",
            new_callable=AsyncMock,
        ) as mock_chat:
            from datetime import datetime, timezone
            mock_chat.return_value = ChatResponse(
                session_id="test-session",
                message="Hello from Nexxi!",
                model="Test-Model",
                tokens_used=10,
                response_time_ms=100.0,
                timestamp=datetime.now(timezone.utc),
            )

            response = await client.post(
                "/v1/chat",
                json={"message": "Hello Nexxi!"},
                headers={"X-API-Key": TEST_API_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_empty_message_rejected(self, client):
        """Empty message should be rejected at schema validation level."""
        response = await client.post(
            "/v1/chat",
            json={"message": ""},
            headers={"X-API-Key": TEST_API_KEY},
        )
        # Should be 422 (Pydantic validation) or 400 (safety filter)
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_message_too_long_rejected(self, client):
        """Messages exceeding 1000 chars should be rejected."""
        response = await client.post(
            "/v1/chat",
            json={"message": "a" * 1001},
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert response.status_code in (400, 422)
