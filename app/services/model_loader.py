"""
app/services/model_loader.py

Hugging Face model loader with singleton pattern.

Design Decisions:
- Singleton via module-level state (thread-safe for Python's GIL).
  FastAPI runs in a single process by default; for multi-worker setups,
  use a shared memory or model-server pattern (e.g. vLLM, TGI).
- HF_TOKEN is read exclusively from the environment — never a
  function argument or config file value.
- 4-bit quantization (BitsAndBytes NF4) dramatically reduces VRAM
  usage: Mistral-7B goes from ~14GB to ~4GB, fitting on a single A40.
- CPU fallback is automatic: if no CUDA device is detected, the model
  loads in float32 on CPU with quantization disabled.
- Warm-up on startup sends a silent token-generation pass so the
  first real user request doesn't experience cold-start latency.
"""

from __future__ import annotations

import os
import time
from typing import Any

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    TextIteratorStreamer,
)

from app.utils.exceptions import ConfigurationError, ModelLoadError, ModelNotLoadedError
from app.utils.logger import get_logger
from app.utils.metrics import model_gpu_memory_used_bytes, model_loaded, record_gpu_memory

logger = get_logger(__name__)

# ── Singleton state ───────────────────────────────────────────
# Stored at module level; populated once during lifespan startup.
_model: PreTrainedModel | None = None
_tokenizer: PreTrainedTokenizerBase | None = None
_model_name: str = ""
_device: str = "cpu"


def _resolve_device(requested: str = "auto") -> str:
    """
    Determine the appropriate compute device.

    Args:
        requested: 'auto' | 'cuda' | 'cpu'

    Returns:
        Resolved device string ('cuda' or 'cpu').
    """
    if requested == "cpu":
        return "cpu"
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"GPU detected: {gpu_name} — using CUDA")
        return device
    logger.warning("No GPU detected — falling back to CPU. Inference will be slow.")
    return "cpu"


def _build_quantization_config(
    quantization: str, device: str
) -> BitsAndBytesConfig | None:
    """
    Build a BitsAndBytesConfig for quantized loading.

    Args:
        quantization: '4bit' | '8bit' | 'none'
        device: 'cuda' | 'cpu'

    Returns:
        BitsAndBytesConfig or None if quantization is disabled / unsupported.
    """
    # BitsAndBytes quantization requires CUDA
    if device == "cpu":
        if quantization != "none":
            logger.warning(
                "Quantization requires CUDA. Disabling for CPU inference."
            )
        return None

    if quantization == "4bit":
        logger.info("Loading with 4-bit NF4 quantization (BitsAndBytes)")
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",         # NF4 is optimal for LLMs
            bnb_4bit_use_double_quant=True,     # Nested quantization saves ~0.4 bits/param
        )
    elif quantization == "8bit":
        logger.info("Loading with 8-bit LLM.int8 quantization")
        return BitsAndBytesConfig(load_in_8bit=True)

    logger.info("No quantization — loading in full precision (float16 on GPU)")
    return None


def load_model(
    model_name: str | None = None,
    device: str = "auto",
    quantization: str = "4bit",
) -> tuple[PreTrainedModel, PreTrainedTokenizerBase]:
    """
    Load the Hugging Face model and tokeniser (singleton).

    On subsequent calls, returns the already-loaded objects without
    re-downloading or re-allocating VRAM.

    Args:
        model_name: HF model identifier. Defaults to HF_MODEL_NAME env var.
        device: Compute device hint ('auto', 'cuda', 'cpu').
        quantization: Quantization strategy ('4bit', '8bit', 'none').

    Returns:
        Tuple of (model, tokenizer).

    Raises:
        ConfigurationError: If HF_TOKEN or model name is missing.
        ModelLoadError: If the model fails to load from Hugging Face Hub.
    """
    global _model, _tokenizer, _model_name, _device

    # Return early if already loaded (singleton)
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer

    # ── Resolve model name ────────────────────────────────────
    resolved_name = model_name or os.environ.get("HF_MODEL_NAME", "")
    if not resolved_name:
        raise ConfigurationError(
            "Model name not specified.",
            detail="Set HF_MODEL_NAME in your .env file.",
        )

    # ── Read HF token securely from environment ───────────────
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        raise ConfigurationError(
            "Hugging Face token not found.",
            detail="Set HF_TOKEN in your .env file. Get one at https://huggingface.co/settings/tokens",
        )

    # ── Device resolution ─────────────────────────────────────
    resolved_device = _resolve_device(device)
    quant_config = _build_quantization_config(quantization, resolved_device)

    logger.info(
        "Loading model from Hugging Face Hub",
        model=resolved_name,
        device=resolved_device,
        quantization=quantization,
    )

    start = time.monotonic()
    try:
        # ── Tokenizer ──────────────────────────────────────────
        tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(
            resolved_name,
            token=hf_token,
            use_fast=True,       # Rust-based fast tokenizer
            padding_side="left", # Required for batch inference
        )
        # Ensure a pad token exists (many instruction models don't set one)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # ── Model ──────────────────────────────────────────────
        load_kwargs: dict[str, Any] = {
            "token": hf_token,
            "device_map": resolved_device if resolved_device == "cuda" else None,
            "torch_dtype": torch.float16 if resolved_device == "cuda" else torch.float32,
            "trust_remote_code": False,      # Security: never trust arbitrary code
            "low_cpu_mem_usage": True,       # Load shard-by-shard to reduce peak RAM
        }
        if quant_config:
            load_kwargs["quantization_config"] = quant_config

        model: PreTrainedModel = AutoModelForCausalLM.from_pretrained(
            resolved_name,
            **load_kwargs,
        )
        model.eval()  # Disable dropout / training-mode behaviour

    except Exception as exc:
        logger.error(f"Failed to load model: {exc}")
        raise ModelLoadError(
            "Model failed to load.",
            detail="Check HF_TOKEN validity, model name, and network connectivity.",
        ) from exc

    elapsed = time.monotonic() - start
    logger.info(f"Model loaded successfully in {elapsed:.2f}s", model=resolved_name)

    # ── Warm-up pass ──────────────────────────────────────────
    _warmup(model, tokenizer, resolved_device)

    # ── Store singleton state ──────────────────────────────────
    _model = model
    _tokenizer = tokenizer
    _model_name = resolved_name
    _device = resolved_device

    # ── Update metrics ─────────────────────────────────────────
    model_loaded.set(1)
    record_gpu_memory()

    return _model, _tokenizer


def _warmup(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    device: str,
) -> None:
    """
    Run a silent warm-up pass to JIT-compile kernels and reduce
    first-request latency.
    """
    logger.info("Running model warm-up pass...")
    try:
        inputs = tokenizer("Hello", return_tensors="pt")
        if device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.inference_mode():
            model.generate(**inputs, max_new_tokens=5, do_sample=False)
        logger.info("Model warm-up complete")
    except Exception as exc:
        # Non-fatal — warm-up failure should not block startup
        logger.warning(f"Warm-up failed (non-critical): {exc}")


def get_model() -> PreTrainedModel:
    """
    Return the loaded model.

    Raises:
        ModelNotLoadedError: If load_model() hasn't been called yet.
    """
    if _model is None:
        raise ModelNotLoadedError(
            "Model is not loaded.",
            detail="Ensure load_model() is called during application startup.",
        )
    return _model


def get_tokenizer() -> PreTrainedTokenizerBase:
    """
    Return the loaded tokenizer.

    Raises:
        ModelNotLoadedError: If load_model() hasn't been called yet.
    """
    if _tokenizer is None:
        raise ModelNotLoadedError(
            "Tokenizer is not loaded.",
            detail="Ensure load_model() is called during application startup.",
        )
    return _tokenizer


def get_model_name() -> str:
    """Return the short, user-facing model label (hides HF repo details)."""
    # We intentionally return only the repo name without org prefix
    # to avoid revealing internal model provenance to API clients.
    return _model_name.split("/")[-1] if "/" in _model_name else _model_name


def create_streamer(skip_prompt: bool = True) -> TextIteratorStreamer:
    """
    Create a TextIteratorStreamer for token-by-token streaming.

    Args:
        skip_prompt: If True, the streamer skips the prompt tokens
                     and only yields generated text.

    Returns:
        A TextIteratorStreamer bound to the loaded tokenizer.
    """
    return TextIteratorStreamer(
        get_tokenizer(),  # type: ignore[arg-type]
        skip_prompt=skip_prompt,
        skip_special_tokens=True,
    )


def unload_model() -> None:
    """
    Release model from memory.
    Use during graceful shutdown or test teardown.
    """
    global _model, _tokenizer

    if _model is not None:
        del _model
        _model = None

    if _tokenizer is not None:
        del _tokenizer
        _tokenizer = None

    # Free VRAM on GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    model_loaded.set(0)
    logger.info("Model unloaded and VRAM released")
