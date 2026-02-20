# Changelog

All notable changes to Nexxi are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] - 2025-02-20

### Added
- Initial production-ready release of Nexxi
- FastAPI backend with API key authentication middleware
- Hugging Face model loader with 4-bit/8-bit quantization and CPU fallback
- Redis-backed conversation session manager with sliding window history
- Multi-layer safety filter: HTML sanitisation, PII redaction, injection detection
- Standard and Server-Sent Events streaming chat endpoints
- Prometheus metrics covering four golden signals
- Structured JSON logging with per-request correlation IDs
- Docker multi-stage build with non-root user
- Docker Compose stack: app, Redis, PostgreSQL, Prometheus, Grafana
- GitHub Actions CI pipeline: lint, test, security scan, Docker build, push
- GitHub Actions CD pipeline with manual approval gate
- Comprehensive unit and integration test suite (80%+ coverage target)
- Full API documentation via Swagger UI and ReDoc

---

## [Unreleased]

### Planned
- LangChain tool-use integration (web search, calculator)
- OpenTelemetry distributed tracing
- PostgreSQL conversation persistence (currently Redis-only)
- Webhook support for async long-running requests
- Admin dashboard for session management
