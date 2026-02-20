# Nexxi API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints marked 🔒 require the `X-API-Key` header.

```
X-API-Key: your_api_key_here
```

---

## Endpoints

### 🔒 POST /v1/chat

Send a message and receive a complete response.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | ✅ | User message (1–1000 chars) |
| `session_id` | string (UUID4) | ❌ | Omit to start a new session |
| `stream` | boolean | ❌ | Stream via SSE (default: false) |

**Response 200**:

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |
| `message` | string | Nexxi's response |
| `model` | string | Model label |
| `tokens_used` | integer | Output token count |
| `response_time_ms` | float | Latency in ms |
| `timestamp` | datetime | UTC timestamp |

**Error Responses**:
- `400` — Safety violation or bad input
- `401` — Missing/invalid API key
- `422` — Schema validation error
- `429` — Rate limit exceeded
- `503` — Model not loaded

---

### 🔒 POST /v1/chat/stream

Stream a response via Server-Sent Events.

Each event: `data: {"session_id":"...","delta":"...","finished":false}`

Final event: `data: {"session_id":"...","delta":"","finished":true}`

---

### 🔒 DELETE /v1/chat/session

Clear conversation history for a session.

```json
{"session_id": "550e8400-e29b-41d4-a716-446655440000"}
```

---

### GET /health

Liveness probe — no auth required.

```json
{"status": "ok", "service": "Nexxi", "timestamp": "..."}
```

---

### GET /ready

Readiness probe — checks model + Redis.

```json
{
  "status": "ready",
  "model_loaded": true,
  "redis_connected": true,
  "details": {"model": "loaded", "redis": "connected"}
}
```

---

### GET /metrics

Prometheus metrics endpoint — no auth required.

---

### GET /docs

Swagger UI — only available in development/staging.

---

## Error Schema

All errors follow this structure:

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "detail": "You have exceeded 60 requests per minute.",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Rate Limits

- 60 requests per minute per API key
- Applied to all `/v1/*` endpoints
- Response includes `Retry-After` header when limited
