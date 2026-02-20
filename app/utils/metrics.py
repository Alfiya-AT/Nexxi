"""
app/utils/metrics.py

Prometheus metrics definitions for Nexxi.

Design Decisions:
- Metrics are defined at module level (singletons) so they can
  be imported anywhere without double-registration.
- We track the four golden signals: latency, traffic, errors, saturation.
- Label cardinality is kept low (no user IDs) to avoid memory bloat.
- prometheus-fastapi-instrumentator handles HTTP-level metrics;
  these are application-level business metrics.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Summary

# ── Traffic ───────────────────────────────────────────────────

chat_requests_total = Counter(
    name="nexxi_chat_requests_total",
    documentation="Total number of chat requests received",
    labelnames=["model", "env"],
)

streaming_requests_total = Counter(
    name="nexxi_streaming_requests_total",
    documentation="Total number of streaming (SSE) chat requests",
    labelnames=["model"],
)

# ── Latency (four quadrants of LLM latency) ──────────────────

inference_latency_seconds = Histogram(
    name="nexxi_inference_latency_seconds",
    documentation="Time taken by model inference (generation only)",
    labelnames=["model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, float("inf")),
)

total_request_latency_seconds = Histogram(
    name="nexxi_total_request_latency_seconds",
    documentation="End-to-end request latency including safety checks and serialisation",
    labelnames=["endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, float("inf")),
)

tokens_generated = Summary(
    name="nexxi_tokens_generated",
    documentation="Distribution of output token counts per response",
)

# ── Errors ────────────────────────────────────────────────────

inference_errors_total = Counter(
    name="nexxi_inference_errors_total",
    documentation="Total number of model inference failures",
    labelnames=["error_type"],
)

safety_violations_total = Counter(
    name="nexxi_safety_violations_total",
    documentation="Total inputs blocked by the safety filter",
    labelnames=["reason"],
)

rate_limit_hits_total = Counter(
    name="nexxi_rate_limit_hits_total",
    documentation="Number of requests rejected due to rate limiting",
)

# ── Saturation / Resource ─────────────────────────────────────

model_gpu_memory_used_bytes = Gauge(
    name="nexxi_model_gpu_memory_used_bytes",
    documentation="GPU memory currently allocated to the model (bytes)",
    labelnames=["device"],
)

active_sessions_count = Gauge(
    name="nexxi_active_sessions_count",
    documentation="Number of active conversation sessions in Redis",
)

model_loaded = Gauge(
    name="nexxi_model_loaded",
    documentation="1 if the LLM is loaded and ready, 0 otherwise",
)


def record_gpu_memory() -> None:
    """
    Sample current GPU memory usage from PyTorch and update the gauge.
    Safe to call even when running on CPU (no-op in that case).
    """
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                used = torch.cuda.memory_allocated(i)
                model_gpu_memory_used_bytes.labels(device=f"cuda:{i}").set(used)
    except Exception:
        # Non-fatal — metrics should never crash the app
        pass
