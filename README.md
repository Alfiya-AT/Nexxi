# Nexxi — Next-Gen AI Chatbot

> **_Next-gen answers, right now._**

[![CI](https://github.com/your-org/nexxi/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/nexxi/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

**Nexxi** is a production-ready, enterprise-grade AI chatbot powered by [Hugging Face](https://huggingface.co/) Transformers. It is designed for scalability, security, and observability — suitable for internal tooling, customer support, or developer APIs.

**Key traits:**
- 🧠 **Smart** — Backed by Mistral-7B-Instruct (configurable)
- 🔒 **Secure** — Zero hardcoded credentials, multi-layer safety filters
- 📈 **Observable** — Prometheus metrics + structured JSON logging
- 🚀 **Scalable** — Redis-backed sessions, Docker-ready
- 🧪 **Testable** — 80%+ test coverage target, full mock support

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                               │
│              (Browser / Mobile / API Consumer)              │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS  X-API-Key
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEXXI API (FastAPI)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Auth MW     │  │  Rate Limit  │  │  Logging MW      │  │
│  │ (API Key)    │  │  (slowapi)   │  │  (Structured)    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┼─────────────────────┘          │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ROUTES  /v1/chat  /health               │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  CHAT SERVICE                        │   │
│  │                                                      │   │
│  │  SafetyFilter ──► ConversationManager ──► ModelGen  │   │
│  │  (PII, inject,     (Redis sessions,     (HuggingFace│   │
│  │   jailbreak)        sliding window)      Transformers│   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│              ┌────────────┼──────────────┐                  │
│              ▼            ▼              ▼                  │
│           REDIS         MODEL         POSTGRES              │
│         (Sessions)  (HF Mistral-7B)  (Storage)             │
└─────────────────────────────────────────────────────────────┘
                             │
               ┌─────────────┴──────────────┐
               ▼                            ▼
          PROMETHEUS                    GRAFANA
          (Metrics)                   (Dashboard)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.111 + Uvicorn |
| LLM | Mistral-7B-Instruct (HuggingFace Transformers) |
| Quantization | BitsAndBytes (4-bit NF4) |
| Session Store | Redis 7 |
| Database | PostgreSQL 16 |
| Auth | API Key (X-API-Key header) |
| Rate Limiting | slowapi + Redis |
| Logging | Loguru (structured JSON) |
| Metrics | Prometheus + Grafana |
| Testing | pytest + httpx (asyncio) |
| Containers | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Prerequisites

- Python **3.11+**
- Docker + Docker Compose (for full stack)
- A [Hugging Face account](https://huggingface.co) with API token
- GPU with ≥ 8GB VRAM recommended (CPU fallback available)

---

## Quick Start (5 Steps)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/nexxi.git
cd nexxi
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your actual values:
# HF_TOKEN=hf_...          ← your Hugging Face token
# API_KEY=...              ← choose a strong key
# APP_SECRET_KEY=...       ← generate: openssl rand -hex 32
```

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Start the full stack (Docker)

```bash
docker compose --env-file .env -f docker/docker-compose.yml up
```

### 5. Test the API

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Nexxi!"}'
```

---

## Environment Variables

**Never commit `.env`** — only `.env.example` is safe to commit.

Refer to `.env.example` for a complete list of required variables.

| Variable | Description |
|---|---|
| `HF_TOKEN` | Hugging Face API token (required) |
| `HF_MODEL_NAME` | Model repo path (default: Mistral-7B-Instruct-v0.3) |
| `API_KEY` | API key for X-API-Key authentication |
| `APP_SECRET_KEY` | Application secret (≥ 32 chars) |
| `REDIS_URL` | Redis connection string |
| `DATABASE_URL` | PostgreSQL connection string |
| `LOG_LEVEL` | DEBUG / INFO / WARNING / ERROR |
| `APP_ENV` | development / staging / production |

---

## API Reference

### Authentication

All chat endpoints require the `X-API-Key` header:

```
X-API-Key: your_api_key_here
```

### Endpoints

#### `POST /v1/chat`
Send a message and receive a complete response.

**Request:**
```json
{
  "session_id": "optional-uuid-v4",
  "message": "What is machine learning?",
  "stream": false
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Machine learning is a branch of AI...",
  "model": "Mistral-7B-Instruct-v0.3",
  "tokens_used": 128,
  "response_time_ms": 1240.5,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

#### `POST /v1/chat/stream`
Stream a response token-by-token via Server-Sent Events.

Each SSE event is a JSON `StreamChunk`:
```json
{"session_id": "...", "delta": "Machine", "finished": false}
{"session_id": "...", "delta": " learning", "finished": false}
{"session_id": "...", "delta": "", "finished": true}
```

#### `DELETE /v1/chat/session`
Clear a conversation's history.

```json
{"session_id": "550e8400-e29b-41d4-a716-446655440000"}
```

#### `GET /health`
Liveness check — returns `200 OK` if the service is running.

#### `GET /ready`
Readiness check — returns `200` only if model + Redis are healthy.

#### `GET /metrics`
Prometheus metrics endpoint (no auth required).

#### `GET /docs`
Swagger UI (disabled in production).

---

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=html

# Integration tests (requires Redis)
pytest tests/integration/ -v

# Fast run (skip slow tests)
pytest -m "not slow" -v
```

---

## Deployment Guide

### Docker (Recommended)

```bash
# Build the production image
docker build -f docker/Dockerfile -t nexxi-app:latest .

# Run with environment variables (NEVER bake secrets into image)
docker run -p 8000:8000 \
  --env-file .env \
  --gpus all \
  nexxi-app:latest
```

### Docker Compose (Full Stack)

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

Dashboard URLs after startup:
- **API**: http://localhost:8000
- **Swagger**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin / see GRAFANA_PASSWORD in .env)

### GPU Support

For CUDA support, install the CUDA-enabled PyTorch:
```bash
pip install torch==2.3.0+cu121 --index-url https://download.pytorch.org/whl/cu121
```

---

## Security Notes

1. **Zero hardcoded credentials** — all secrets are in `.env` (never committed)
2. **PII redaction** — emails, phones, SSNs are redacted before logging
3. **Prompt injection protection** — heuristic + pattern-based detection
4. **Timing-safe API key comparison** — `hmac.compare_digest()` prevents timing attacks
5. **Non-root Docker user** — the container runs as `nexxi` (UID 1001)
6. **Bandit SAST** — runs on every CI pipeline

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT License](LICENSE) — © 2025 Nexxi Team
