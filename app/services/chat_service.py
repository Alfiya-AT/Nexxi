"""
app/services/chat_service.py

Core chat business logic for Nexxi.

Flow:
    1. Safety filter → clean input or raise
    2. Session management → load or create session
    3. Add user message to history
    4. Build prompt from conversation history
    5. Run model inference (standard or streaming)
    6. Add assistant response to history
    7. Return structured response

Design Decisions:
- Service layer is async to align with FastAPI's async routes and
  allow non-blocking Redis/model calls.
- Model inference is run in a ThreadPoolExecutor (via asyncio's
  run_in_executor) because HuggingFace's generate() is synchronous.
  This prevents blocking the event loop during inference.
- Tokens are counted post-generation using the tokenizer's encode
  method — this is the most accurate approach.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator

import torch

from app.services.conversation_manager import ConversationManager
from app.services.model_loader import get_model, get_model_name, get_tokenizer, create_streamer
from app.services.safety_filter import SafetyFilter
from app.schemas.chat_schema import ChatResponse, StreamChunk
from app.utils.exceptions import InferenceError, SafetyFilterError
from app.utils.logger import get_logger
from app.utils.metrics import (
    chat_requests_total,
    inference_errors_total,
    inference_latency_seconds,
    tokens_generated,
    total_request_latency_seconds,
)

logger = get_logger(__name__)

# Shared thread pool for synchronous inference calls
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nexxi-inference")

# ── Mistral instruction format ─────────────────────────────────
# Mistral uses the [INST] ... [/INST] template for chat
_INST_START = "[INST]"
_INST_END = "[/INST]"
_BOS = "<s>"


def _build_mistral_prompt(messages: list[dict[str, str]]) -> str:
    """
    Convert conversation history to Mistral's instruction format.

    Mistral chat template:
        <s>[INST] system_prompt + first_user_msg [/INST] assistant_msg </s>
        <s>[INST] next_user_msg [/INST] next_assistant_msg </s>
        <s>[INST] latest_user_msg [/INST]

    Args:
        messages: List of {"role": ..., "content": ...} dicts.

    Returns:
        Formatted prompt string ready for tokenization.
    """
    prompt = ""
    system_content = ""

    # Extract system prompt
    non_system = []
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            non_system.append(msg)

    # Pair user/assistant messages
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(non_system) - 1:
        user_msg = non_system[i]
        asst_msg = non_system[i + 1]
        if user_msg["role"] == "user" and asst_msg["role"] == "assistant":
            pairs.append((user_msg["content"], asst_msg["content"]))
            i += 2
        else:
            i += 1

    # Latest user message (unanswered)
    latest_user = non_system[-1]["content"] if non_system else ""

    # First exchange includes system prompt
    for idx, (user, asst) in enumerate(pairs):
        if idx == 0 and system_content:
            prompt += f"{_BOS}{_INST_START} {system_content}\n\n{user} {_INST_END} {asst} </s>"
        else:
            prompt += f"{_BOS}{_INST_START} {user} {_INST_END} {asst} </s>"

    # Final unanswered user turn
    if latest_user:
        if not pairs and system_content:
            prompt += f"{_BOS}{_INST_START} {system_content}\n\n{latest_user} {_INST_END}"
        else:
            prompt += f"{_BOS}{_INST_START} {latest_user} {_INST_END}"

    return prompt


class ChatService:
    """
    Orchestrates the full chat request pipeline.

    Args:
        conversation_manager: Session/history store.
        safety_filter: Input/output safety checks.
        max_new_tokens: Maximum tokens to generate per response.
        temperature: Sampling temperature.
        top_p: Nucleus sampling threshold.
        repetition_penalty: Penalise token repetition.
    """

    def __init__(
        self,
        conversation_manager: ConversationManager,
        safety_filter: SafetyFilter,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
    ) -> None:
        self._conv_manager = conversation_manager
        self._safety = safety_filter
        self._max_new_tokens = max_new_tokens
        self._temperature = temperature
        self._top_p = top_p
        self._rep_penalty = repetition_penalty

    async def chat(
        self, session_id: str, user_message: str
    ) -> ChatResponse:
        """
        Process a single-turn chat request.

        Args:
            session_id: Must be an existing or newly created session.
            user_message: Raw user input (will be safety-filtered).

        Returns:
            ChatResponse with Nexxi's reply and metadata.

        Raises:
            SafetyFilterError: If input fails safety checks.
            InferenceError: If model generation fails.
        """
        request_start = time.monotonic()

        # ── Safety check ──────────────────────────────────────
        clean_input = self._safety.check_or_raise(user_message)

        # ── Load or initialise session ────────────────────────
        exists = await self._conv_manager.session_exists(session_id)
        if not exists:
            await self._conv_manager.initialise_session(session_id)

        # ── Append user message ───────────────────────────────
        await self._conv_manager.add_user_message(session_id, clean_input)

        # ── Summarize if needed ───────────────────────────────
        if await self._conv_manager.should_summarize(session_id):
            await self._maybe_summarize(session_id)

        # ── Get history and build prompt ──────────────────────
        history = await self._conv_manager.get_history(session_id)
        prompt = _build_mistral_prompt(history)

        # ── Run inference (non-blocking via executor) ─────────
        inference_start = time.monotonic()
        try:
            response_text = await asyncio.get_event_loop().run_in_executor(
                _executor,
                lambda: self._generate(prompt),
            )
        except Exception as exc:
            inference_errors_total.labels(error_type="generation_failed").inc()
            logger.error(f"Inference failed: {exc}")
            raise InferenceError("Model failed to generate a response.") from exc
        finally:
            inference_elapsed = time.monotonic() - inference_start
            inference_latency_seconds.labels(model=get_model_name()).observe(
                inference_elapsed
            )

        # ── Count tokens ──────────────────────────────────────
        token_count = len(get_tokenizer().encode(response_text))
        tokens_generated.observe(token_count)

        # ── Persist assistant response ────────────────────────
        await self._conv_manager.add_assistant_message(session_id, response_text)

        # ── Metrics & logging ──────────────────────────────────
        total_elapsed = time.monotonic() - request_start
        total_request_latency_seconds.labels(endpoint="/v1/chat").observe(total_elapsed)
        chat_requests_total.labels(model=get_model_name(), env="production").inc()

        logger.info(
            "Chat response generated",
            session_id=session_id,
            tokens=token_count,
            latency_ms=round(total_elapsed * 1000, 2),
        )

        return ChatResponse(
            session_id=session_id,
            message=response_text,
            model=get_model_name(),
            tokens_used=token_count,
            response_time_ms=round(total_elapsed * 1000, 2),
        )

    async def stream_chat(
        self, session_id: str, user_message: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Process a streaming chat request using Server-Sent Events.

        Yields StreamChunk objects as tokens are generated.
        The final chunk has finished=True.

        Args:
            session_id: Session identifier.
            user_message: Raw user input.

        Yields:
            StreamChunk with partial response text.
        """
        # ── Safety check ──────────────────────────────────────
        try:
            clean_input = self._safety.check_or_raise(user_message)
        except SafetyFilterError as exc:
            yield StreamChunk(session_id=session_id, error=str(exc), finished=True)
            return

        # ── Session and history ───────────────────────────────
        exists = await self._conv_manager.session_exists(session_id)
        if not exists:
            await self._conv_manager.initialise_session(session_id)

        await self._conv_manager.add_user_message(session_id, clean_input)
        history = await self._conv_manager.get_history(session_id)
        prompt = _build_mistral_prompt(history)

        # ── Streaming inference ───────────────────────────────
        streamer = create_streamer(skip_prompt=True)
        full_response = ""

        def _generate_streaming() -> None:
            """Run generate() with the streamer in a background thread."""
            tokenizer = get_tokenizer()
            model = get_model()
            inputs = tokenizer(prompt, return_tensors="pt")

            if next(model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}

            model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=self._max_new_tokens,
                temperature=self._temperature,
                top_p=self._top_p,
                repetition_penalty=self._rep_penalty,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # Start generation in background thread
        loop = asyncio.get_event_loop()
        generation_task = loop.run_in_executor(_executor, _generate_streaming)

        # Stream tokens to client
        for token_text in streamer:
            full_response += token_text
            yield StreamChunk(
                session_id=session_id,
                delta=token_text,
                finished=False,
            )

        await generation_task  # Ensure thread completes before cleanup
        await self._conv_manager.add_assistant_message(session_id, full_response)

        yield StreamChunk(session_id=session_id, delta="", finished=True)

    def _generate(self, prompt: str) -> str:
        """
        Synchronous text generation call (runs in ThreadPoolExecutor).

        Args:
            prompt: Formatted prompt string.

        Returns:
            Generated response text (prompt stripped).
        """
        tokenizer = get_tokenizer()
        model = get_model()

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=3072,        # Leave room for max_new_tokens
        )

        # Move to GPU if model is on GPU
        if next(model.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                temperature=self._temperature,
                top_p=self._top_p,
                repetition_penalty=self._rep_penalty,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens (skip the prompt)
        prompt_length = inputs["input_ids"].shape[1]
        generated_ids = output_ids[:, prompt_length:]
        response = tokenizer.decode(
            generated_ids[0],
            skip_special_tokens=True,
        ).strip()

        return response

    async def _maybe_summarize(self, session_id: str) -> None:
        """
        Generate a summary of the conversation history and apply it.
        This keeps the context window from overflowing.
        """
        logger.info(f"Triggering conversation summary for session {session_id}")
        history = await self._conv_manager.get_history(session_id)

        # Build a summarization prompt
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history
            if m["role"] != "system"
        )
        summary_prompt = (
            f"Summarize this conversation concisely in 2-3 sentences:\n\n"
            f"{history_text}\n\nSummary:"
        )

        try:
            summary = await asyncio.get_event_loop().run_in_executor(
                _executor,
                lambda: self._generate(summary_prompt),
            )
            await self._conv_manager.apply_summary(session_id, summary)
        except Exception as exc:
            # Non-fatal: continue without summary if it fails
            logger.warning(f"Summarization failed: {exc}")

    async def delete_session(self, session_id: str) -> None:
        """Delete a user's conversation session."""
        await self._conv_manager.delete_session(session_id)
