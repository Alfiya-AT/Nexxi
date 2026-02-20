"""
tests/unit/test_conversation_manager.py

Unit tests for ConversationManager.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.services.conversation_manager import ConversationManager
from app.utils.exceptions import SessionNotFoundError


SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"


def _make_session(messages: list | None = None, turn_count: int = 0) -> str:
    return json.dumps({
        "session_id": SESSION_ID,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "turn_count": turn_count,
        "messages": messages or [{"role": "system", "content": "You are Nexxi."}],
    })


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=_make_session())
    r.setex = AsyncMock(return_value=True)
    r.exists = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    return r


@pytest.fixture
def manager(mock_redis):
    return ConversationManager(redis_client=mock_redis, max_history_turns=3)


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_create_session_returns_uuid(self, manager):
        sid = manager.create_session()
        import re
        assert re.match(r"[0-9a-f\-]{36}", sid)

    @pytest.mark.asyncio
    async def test_initialise_session_writes_to_redis(self, manager, mock_redis):
        await manager.initialise_session(SESSION_ID)
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_not_found_raises(self, manager, mock_redis):
        mock_redis.exists = AsyncMock(return_value=False)
        mock_redis.get = AsyncMock(return_value=None)
        with pytest.raises(SessionNotFoundError):
            await manager.get_history("nonexistent-session")

    @pytest.mark.asyncio
    async def test_delete_session_calls_redis(self, manager, mock_redis):
        await manager.delete_session(SESSION_ID)
        mock_redis.delete.assert_called_once()


class TestMessageManagement:
    @pytest.mark.asyncio
    async def test_add_user_message(self, manager, mock_redis):
        await manager.add_user_message(SESSION_ID, "Hello!")
        mock_redis.setex.assert_called()
        saved = json.loads(mock_redis.setex.call_args[0][2])
        messages = saved["messages"]
        assert any(m["role"] == "user" and m["content"] == "Hello!" for m in messages)

    @pytest.mark.asyncio
    async def test_add_assistant_message_increments_turn_count(self, manager, mock_redis):
        await manager.add_assistant_message(SESSION_ID, "Hi!")
        saved = json.loads(mock_redis.setex.call_args[0][2])
        assert saved["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_system_prompt_always_first(self, manager, mock_redis):
        history = await manager.get_history(SESSION_ID)
        assert history[0]["role"] == "system"


class TestSlidingWindow:
    @pytest.mark.asyncio
    async def test_old_turns_pruned_when_over_limit(self, mock_redis):
        """When max_history_turns=1, only the latest turn should be kept."""
        manager = ConversationManager(redis_client=mock_redis, max_history_turns=1)
        session_with_history = _make_session(messages=[
            {"role": "system", "content": "You are Nexxi."},
            {"role": "user", "content": "Old turn user"},
            {"role": "assistant", "content": "Old turn assistant"},
            {"role": "user", "content": "Recent turn user"},
            {"role": "assistant", "content": "Recent turn assistant"},
        ], turn_count=2)
        mock_redis.get = AsyncMock(return_value=session_with_history)

        await manager.add_user_message(SESSION_ID, "New message")
        saved = json.loads(mock_redis.setex.call_args[0][2])
        # System message should always be preserved
        assert saved["messages"][0]["role"] == "system"
