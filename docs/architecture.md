# Nexxi Architecture

## System Design

Nexxi follows a layered, clean-architecture pattern:

```
HTTP Layer      → FastAPI routes + middleware
Service Layer   → ChatService, ConversationManager, SafetyFilter
Infrastructure  → ModelLoader (HuggingFace), Redis, PostgreSQL
Observability   → Prometheus metrics, Loguru structured logging
```

## Request Lifecycle

```
1. HTTP Request arrives
2. RequestLoggingMiddleware injects correlation ID
3. APIKeyMiddleware validates X-API-Key (timing-safe comparison)
4. Rate limiter checks quota (Redis-backed, per API key)
5. Route handler calls ChatService.chat()
6. SafetyFilter.check_or_raise() — PII redaction + injection detection
7. ConversationManager.get_history() — load session from Redis
8. Mistral prompt is constructed from history
9. Model inference runs in ThreadPoolExecutor (non-blocking)
10. Response persisted to session history
11. ChatResponse returned to client
12. Prometheus metrics updated
```

## Concurrency Model

- FastAPI runs on a single Uvicorn worker (shared model memory)
- Model inference runs in `ThreadPoolExecutor` via `asyncio.run_in_executor`
  to avoid blocking the event loop
- Redis operations are fully async via `redis.asyncio`

## Session Storage Schema

Redis key: `nexxi:session:{uuid4}`

```json
{
  "session_id": "uuid4",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "turn_count": 5,
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## Security Layers

1. Transport: HTTPS (enforced by reverse proxy)
2. Authentication: X-API-Key header (timing-safe compare)
3. Rate limiting: 60 req/min per API key (Redis-backed)
4. Input filtering: HTML strip + PII redact + injection detect
5. Content moderation: optional ML classifier
6. Container: non-root user, no secrets in image layers

## Scalability Notes

- Current design: single-worker (model in process memory)
- For multi-worker scaling: use vLLM or TGI as a model server,
  then each Nexxi worker makes HTTP calls to the model server
- Sessions in Redis allow any worker to serve any user's request
