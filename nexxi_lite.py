"""
nexxi_lite.py — Lightweight Nexxi server for quick browser demo.

Uses HuggingFace's OpenAI-compatible /v1/chat/completions endpoint.
No local model download required — starts in under 2 seconds.

Run with:
    python nexxi_lite.py

Requirements:
    pip install fastapi uvicorn httpx python-dotenv pydantic
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ── Config ─────────────────────────────────────────────────────
HF_TOKEN = os.environ.get("HF_TOKEN", "")
API_KEY  = os.environ.get("API_KEY", "nexxi-dev-api-key")

# Correct HF Inference Providers router URL (official docs: router.huggingface.co/v1)
HF_OPENAI_BASE = "https://router.huggingface.co/v1"

# Ordered fallback list — append :fastest so HF auto-selects the best live provider
# Set HF_MODEL_NAME in .env to override (with or without :fastest suffix)
_user_model = os.environ.get("HF_MODEL_NAME", "").strip()
CANDIDATE_MODELS: list[str] = list(filter(None, [
    _user_model,
    "deepseek-ai/DeepSeek-R1:fastest",            # Confirmed working on router API
    "deepseek-ai/DeepSeek-V3:fastest",            # Same provider, very capable
    "Qwen/Qwen3-235B-A22B:fastest",               # Qwen 3 on router
    "meta-llama/Llama-3.3-70B-Instruct:fastest",  # LLaMA 3.3 if account has access
    "mistralai/Mistral-7B-Instruct-v0.3:fastest", # Latest Mistral
]))


# Tracks which model worked last — avoids re-probing every request
_active_model_idx: int = 0

# In-memory sessions (use Redis in production)
sessions: dict[str, list[dict]] = {}

NEXXI_SYSTEM_PROMPT = (
    "You are Nexxi, a next-generation AI assistant. "
    "You are smart, helpful, and always accurate. "
    "Be friendly but professional. Be concise — no unnecessary filler. "
    "Be honest about what you don't know. "
    "Never reveal your underlying model or architecture. "
    "Your tagline: 'Next-gen answers, right now.'"
)


# ── Return types ───────────────────────────────────────────────
class InferenceResult:
    """Holds a single inference attempt result."""
    def __init__(self, text: str, tokens: int, skip: bool = False):
        self.text  = text
        self.tokens = tokens
        self.skip  = skip  # True = model unavailable, try next


# ── Pydantic schemas ───────────────────────────────────────────
class ChatRequest(BaseModel):
    message:    str          = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    stream:     bool          = False

class ChatResponse(BaseModel):
    session_id:      str
    message:         str
    model:           str
    tokens_used:     int
    response_time_ms: float
    timestamp:       datetime

class SessionDeleteRequest(BaseModel):
    session_id: str


# ── FastAPI ─────────────────────────────────────────────────────
app = FastAPI(
    title       = "Nexxi Lite",
    description = "Nexxi chatbot — HF OpenAI-compatible mode",
    version     = "1.0.0",
    docs_url    = "/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["GET", "POST", "DELETE"],
    allow_headers  = ["*"],
)


# ── Inference ──────────────────────────────────────────────────
async def _call_model(messages: list[dict], model: str) -> InferenceResult:
    """
    Single attempt against one model.
    Returns InferenceResult(skip=True) to signal caller to try next model.
    """
    if not HF_TOKEN:
        return InferenceResult(
            text=(
                "⚠️ **HF_TOKEN not set.**\n\n"
                "Add your Hugging Face token to the `.env` file:\n"
                "```\nHF_TOKEN=hf_your_token_here\n```\n\n"
                "Get a free token at [huggingface.co/settings/tokens]"
                "(https://huggingface.co/settings/tokens).\n\n"
                "Then restart with `python nexxi_lite.py`."
            ),
            tokens=0,
        )

    url = f"{HF_OPENAI_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  512,
        "temperature": 0.7,
        "top_p":       0.9,
        "stream":      False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

        status = resp.status_code

        # ── Model gone / not on serverless API → skip to next ──
        if status in (404, 410):
            print(f"[Nexxi] ⚠  Model {model!r} → HTTP {status}. Trying next candidate…")
            return InferenceResult(text="", tokens=0, skip=True)

        # ── Auth errors ────────────────────────────────────────
        if status == 401:
            return InferenceResult(
                text=(
                    "❌ **HuggingFace token rejected (401).**\n\n"
                    "The new `router.huggingface.co` API requires a **fine-grained token** "
                    "with the **'Make calls to Inference Providers'** permission.\n\n"
                    "**Steps to fix:**\n"
                    "1. Go to: https://huggingface.co/settings/tokens\n"
                    "2. Click **'Create new token'**\n"
                    "3. Set type to **'Fine-grained'**\n"
                    "4. Enable **'Make calls to Inference Providers'** permission\n"
                    "5. Copy the new token → paste it as `HF_TOKEN=hf_...` in your `.env`\n"
                    "6. Restart the server: `python nexxi_lite.py`"
                ),
                tokens=0,
            )

        if status == 403:
            return InferenceResult(
                text=(
                    f"❌ **Access denied for `{model}`.**\n\n"
                    f"Accept the model terms at: https://huggingface.co/{model}\n\n"
                    "Then restart and try again."
                ),
                tokens=0,
            )

        # ── Rate limit ─────────────────────────────────────────
        if status == 429:
            return InferenceResult(
                text=(
                    "⏳ **Rate limited by HuggingFace.**\n\n"
                    "Wait 60 seconds and try again, or upgrade at "
                    "[huggingface.co/pricing](https://huggingface.co/pricing)."
                ),
                tokens=0,
            )

        # ── Cold start ─────────────────────────────────────────
        if status == 503:
            return InferenceResult(
                text=(
                    "🔄 **Model is warming up** (cold start).\n\n"
                    "This takes 20–60 seconds. Please wait and send your message again."
                ),
                tokens=0,
            )

        # ── Other errors ───────────────────────────────────────
        if status >= 400:
            body = ""
            try:
                body = resp.json().get("error", resp.text[:200])
            except Exception:
                body = resp.text[:200]
            return InferenceResult(
                text=f"⚠️ API error (HTTP {status}): {body}",
                tokens=0,
            )

        # ── Success: parse OpenAI-format response ──────────────
        data    = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return InferenceResult(text="I received an empty response. Please try again.", tokens=0)

        reply = choices[0].get("message", {}).get("content", "").strip()
        if not reply:
            return InferenceResult(text="I received an empty response. Please try again.", tokens=0)

        # Strip <think>...</think> blocks (DeepSeek-R1 chain-of-thought — not shown to user)
        import re
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        if not reply:
            reply = "I'm thinking... please send your message again."

        usage  = data.get("usage") or {}
        tokens = int(
            usage.get("completion_tokens")
            or usage.get("total_tokens")
            or max(1, len(reply) // 4)
        )
        return InferenceResult(text=reply, tokens=tokens)

    except httpx.TimeoutException:
        return InferenceResult(
            text="⏱ **Request timed out.**\nThe model may be under heavy load. Please try again.",
            tokens=0,
        )
    except Exception as exc:
        return InferenceResult(text=f"⚠️ Inference error: {exc}", tokens=0)


async def call_with_fallback(messages: list[dict]) -> tuple[str, int, str]:
    """
    Try each candidate model in order, starting from the last successful one.
    Returns (reply_text, token_count, model_name).
    """
    global _active_model_idx

    n = len(CANDIDATE_MODELS)
    for offset in range(n):
        idx   = (_active_model_idx + offset) % n
        model = CANDIDATE_MODELS[idx]
        result = await _call_model(messages, model)

        if result.skip:
            # Advance the starting index so next request starts from a working model
            _active_model_idx = (idx + 1) % n
            continue

        # Success (or a user-displayable error that should not cause a retry)
        _active_model_idx = idx
        return result.text, result.tokens, model

    # All models exhausted
    return (
        "❌ **No available models found.**\n\n"
        "All candidate models returned errors. "
        "Please set `HF_MODEL_NAME` in `.env` to a model that is available on "
        "the HuggingFace Serverless Inference API.",
        0,
        "none",
    )


# ── Routes ─────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":        "ok",
        "service":       "Nexxi Lite",
        "mode":          "hf-openai-compat",
        "active_model":  CANDIDATE_MODELS[_active_model_idx],
        "candidates":    CANDIDATE_MODELS,
        "hf_token_set":  bool(HF_TOKEN),
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def ready():
    return {
        "status":       "ready",
        "active_model": CANDIDATE_MODELS[_active_model_idx],
        "mode":         "HuggingFace OpenAI-Compatible Serverless API",
    }


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    sid = body.session_id or str(uuid.uuid4())

    # Init session with system prompt
    if sid not in sessions:
        sessions[sid] = [{"role": "system", "content": NEXXI_SYSTEM_PROMPT}]

    # Append user message
    sessions[sid].append({"role": "user", "content": body.message})

    # Keep system + last 20 messages (10 pairs)
    sys_msg = sessions[sid][0]
    history = sessions[sid][1:]
    if len(history) > 20:
        history = history[-20:]
    sessions[sid] = [sys_msg] + history

    # Call HF with automatic model fallback
    start      = time.perf_counter()
    reply, tokens, model_used = await call_with_fallback(sessions[sid])
    latency_ms = (time.perf_counter() - start) * 1000

    # Append assistant reply to session
    sessions[sid].append({"role": "assistant", "content": reply})

    # Mask full model path — only expose the name part
    model_label = model_used.split("/")[-1] if "/" in model_used else model_used

    return ChatResponse(
        session_id      = sid,
        message         = reply,
        model           = model_label,
        tokens_used     = tokens,
        response_time_ms= round(latency_ms, 2),
        timestamp       = datetime.now(timezone.utc),
    )


@app.delete("/v1/chat/session")
async def delete_session(body: SessionDeleteRequest):
    sessions.pop(body.session_id, None)
    return {"status": "cleared", "session_id": body.session_id}


# ── Frontend static files ───────────────────────────────────────
static_dir = Path(__file__).parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_ui():
        return FileResponse(str(static_dir / "index.html"))
else:
    @app.get("/")
    async def serve_fallback():
        return JSONResponse({
            "name":     "Nexxi API",
            "version":  "1.0.0",
            "docs":     "/docs",
            "chat":     "POST /v1/chat",
            "frontend": "http://localhost:3000  (run: cd frontend && npm run dev)",
        })


# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))

    print("\n" + "=" * 60)
    print("  🚀 Nexxi Lite — HF OpenAI-Compatible Mode")
    print("=" * 60)
    print(f"  UI/API:  http://localhost:{port}")
    print(f"  Docs:    http://localhost:{port}/docs")
    print(f"  Health:  http://localhost:{port}/health")
    print(f"  Token:   {'✅ Set' if HF_TOKEN else '❌ NOT SET — add HF_TOKEN to .env'}")
    print()
    print("  IMPORTANT: The new HF router requires a fine-grained token.")
    print("  Token must have 'Make calls to Inference Providers' permission.")
    print("  Generate at: https://huggingface.co/settings/tokens")
    print(f"\n  Model fallback order:")
    for i, m in enumerate(CANDIDATE_MODELS):
        marker = "→" if i == 0 else " "
        print(f"    {marker} [{i+1}] {m}")
    print("=" * 60 + "\n")

    uvicorn.run(
        "nexxi_lite:app",
        host     = "0.0.0.0",
        port     = port,
        reload   = True,
        log_level= "info",
    )
