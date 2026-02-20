# =============================================================
# Nexxi - Multi-stage Production Dockerfile
# =============================================================
# Stage 1 (builder): Install Python dependencies into a venv
# Stage 2 (runtime): Copy only the venv and app code
#
# Benefits:
# - Smaller final image (no build tools)
# - Non-root user for security
# - Healthcheck built in for orchestrators
# - No secrets baked in — pass via --env-file at runtime
# =============================================================

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system build dependencies (required by some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ── Security: non-root user ────────────────────────────────────
RUN groupadd --gid 1001 nexxi && \
    useradd --uid 1001 --gid nexxi --shell /bin/bash --create-home nexxi

WORKDIR /app

# Copy application code (no .env, no models/)
COPY app/ ./app/
COPY config/ ./config/

# Set ownership
RUN chown -R nexxi:nexxi /app

USER nexxi

# ── Environment ────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

EXPOSE 8000

# ── Healthcheck ────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Entrypoint ─────────────────────────────────────────────────
# Secrets are NEVER baked in — pass via: docker run --env-file .env
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
