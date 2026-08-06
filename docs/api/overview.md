# API Overview

The ProofRails API is a REST API served by a FastAPI application.

## Base URL

```
http://localhost:8000          # local development
https://your-deployment.com    # production
```

## Authentication

All endpoints except health and OpenAPI require an `X-API-Key` header:

```
X-API-Key: <your_project_api_key>
```

API keys are scoped to a project. Admin keys grant access to cross-project and analytics endpoints.

Obtain a key by registering a project:

```bash
curl -X POST /v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "owner_wallet": "0x..."}'
```

## Interactive docs

FastAPI auto-generates OpenAPI docs at:

- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc
- `GET /openapi.json` — raw OpenAPI schema

## Rate limiting

Rate limiting is configurable via `RATE_LIMIT_ENABLED` and `RATE_LIMIT_REQUESTS_PER_MINUTE`. Disabled by default in local dev.

## Idempotency

Write endpoints support the `Idempotency-Key` header to prevent duplicate receipts on network retries. Configurable via `IDEMPOTENCY_ENABLED`.

## Response format

Successful responses return JSON. Error responses follow FastAPI's default format:

```json
{
  "detail": "human-readable error message"
}
```

## API sections

- [Receipts](./receipts.md)
- [Verification](./verification.md)
- [Projects](./projects.md)
- [Agents](./agents.md)
- [x402](./x402.md)
- [Anchoring](./anchoring.md)
