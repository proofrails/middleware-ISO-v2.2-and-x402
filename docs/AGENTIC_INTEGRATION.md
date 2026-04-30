# Agentic Integration Guide

This document covers the features added to make the ISO 20022 middleware useful for autonomous agents, LLM-driven workflows, and machine-to-machine integrations.

---

## Table of Contents

1. [Quick Start for Agents](#quick-start-for-agents)
2. [Capability Discovery](#capability-discovery)
3. [Idempotency Keys](#idempotency-keys)
4. [Structured Error Codes](#structured-error-codes)
5. [Operation Status Polling](#operation-status-polling)
6. [Lightweight Receipt Status](#lightweight-receipt-status)
7. [Webhook Subscriptions](#webhook-subscriptions)
8. [Receipt Metadata and Tags](#receipt-metadata-and-tags)
9. [Cursor-Based Pagination](#cursor-based-pagination)
10. [Rate Limit Headers](#rate-limit-headers)
11. [Flare AI Skills Integration](#flare-ai-skills-integration)
12. [Environment Variables](#environment-variables)

---

## Quick Start for Agents

```python
import httpx

BASE = "https://your-middleware.example.com"
HEADERS = {"X-API-Key": "your-key"}

# 1. Discover all available operations
caps = httpx.get(f"{BASE}/v1/capabilities", headers=HEADERS).json()

# 2. Record a payment (idempotent)
receipt = httpx.post(
    f"{BASE}/v1/iso/record-tip",
    headers={**HEADERS, "Idempotency-Key": "unique-client-uuid"},
    json={
        "tip_tx_hash": "0xabc...",
        "chain": "flare",
        "amount": "100.00",
        "currency": "FLR",
        "sender_wallet": "0xsender...",
        "receiver_wallet": "0xreceiver...",
        "reference": "invoice:INV-2024-001",
        "metadata": {"task_id": "task-xyz", "workflow": "payment-reconciliation"},
        "tags": ["batch-1", "priority-high"],
    },
).json()

operation_id = receipt["operation_id"]  # == receipt_id

# 3. Poll status (lightweight)
import time
while True:
    status = httpx.get(f"{BASE}/v1/operations/{operation_id}", headers=HEADERS).json()
    if status["status"] in ("anchored", "failed"):
        break
    time.sleep(3)

# 4. Get live FTSO price for FX enrichment
feed = httpx.get(f"{BASE}/v1/flare/feeds/FLR%2FUSD").json()
print(f"FLR/USD = {feed['price']}")
```

---

## Capability Discovery

**`GET /v1/capabilities`**

Returns the entire API surface as OpenAI-compatible function/tool definitions. Call this once at agent startup to self-configure without hardcoded prompts.

```json
{
  "schema_version": "1.0",
  "service": "ISO 20022 Payment Middleware",
  "tools": [
    {
      "name": "record_payment",
      "description": "...",
      "endpoint": {"method": "POST", "path": "/v1/iso/record-tip"},
      "idempotency_supported": true,
      "x402_cost": null,
      "parameters": { "type": "object", "properties": { ... } }
    },
    ...
  ],
  "flare_protocol": {
    "ftso": { "available_feeds": ["FLR/USD", "BTC/USD", ...] },
    "fdc": { "attestation_types": ["EVMTransaction", "Payment", ...] },
    "networks": { "flare": { "chain_id": 14, "rpc": "..." } }
  }
}
```

Use this with LLM tool-use APIs (OpenAI function calling, Anthropic tool use) by extracting the `tools` array and passing it directly as your tool definitions.

---

## Idempotency Keys

Add `Idempotency-Key: <uuid>` to any `POST`, `PUT`, or `PATCH` request to make it safe to retry.

- The first execution runs normally and caches the response in Redis for **24 hours**.
- Subsequent requests with the same key return the cached response with `Idempotency-Replayed: true`.
- Only **2xx responses** are cached. A 4xx/5xx is not stored, so you can fix the request and retry with the same key.
- Keys are **scoped per API key** (or IP for anonymous callers) to prevent collisions.

```http
POST /v1/iso/record-tip
X-API-Key: your-key
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{ "tip_tx_hash": "0xabc...", ... }
```

```http
HTTP/1.1 200 OK
Idempotency-Replayed: true
Content-Type: application/json

{ "receipt_id": "...", "operation_id": "...", "status": "pending" }
```

**Supported endpoints:** all mutation endpoints (`/iso/record-tip`, `/iso/refund`, `/x402/premium/*`, `/webhooks`, etc.)

---

## Structured Error Codes

All errors follow a consistent envelope. Branch on `code`, not on `message` (which is for humans).

```json
{
  "error": {
    "code": "RECEIPT_NOT_FOUND",
    "message": "Receipt '550e8400...' not found",
    "retryable": false
  }
}
```

When `retryable: true`, the operation is safe to retry after the `retry_after_seconds` window in `details`.

### Error Code Reference

| Code | HTTP | Retryable | Meaning |
|------|------|-----------|---------|
| `RECEIPT_NOT_FOUND` | 404 | false | Receipt ID does not exist |
| `DUPLICATE_TRANSACTION` | 200 | — | Same chain+tx_hash already recorded (returns existing) |
| `ANCHOR_FAILED` | — | true | Anchoring failed; use `/retry-anchor` |
| `ANCHOR_TIMEOUT` | — | true | Blockchain confirmation timed out |
| `UNAUTHORIZED` | 401 | false | No valid API key or SIWE session |
| `RATE_LIMITED` | 429 | true | Request rate exceeded |
| `VALIDATION_ERROR` | 400 | false | Bad request parameter |
| `WEBHOOK_NOT_FOUND` | 404 | false | Webhook subscription not found |
| `WEBHOOK_LIMIT_REACHED` | 409 | false | Project webhook limit (10) reached |
| `OPERATION_NOT_FOUND` | 404 | false | Operation ID not found |
| `FEED_NOT_FOUND` | 404 | false | Unknown FTSO feed symbol |
| `FTSO_UNAVAILABLE` | 503 | true | FTSO feeds disabled or unreachable |
| `FDC_ATTESTATION_FAILED` | 500 | true | FDC verifier request failed |

---

## Operation Status Polling

**`GET /v1/operations/{operation_id}`**

After `record-tip`, the processing pipeline continues asynchronously. Use this lightweight endpoint to poll without fetching the full receipt.

The `operation_id` in the `record-tip` response equals the `receipt_id` — both work interchangeably.

```json
{
  "operation_id": "550e8400-e29b-41d4-a716-446655440000",
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_anchor",
  "bundle_hash": "0xabc123...",
  "flare_txid": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:15Z",
  "error_code": null,
  "error_message": null
}
```

### Pipeline States

```
record-tip → pending → processing → awaiting_anchor → anchored
                                                    ↘ failed
```

| State | Description | Poll interval |
|-------|-------------|---------------|
| `pending` | Queued, not yet picked up | 2–5 s |
| `processing` | Worker generating ISO documents | 2–5 s |
| `awaiting_anchor` | Bundle ready, waiting for chain | 5–10 s |
| `anchored` | Done ✓ | — |
| `failed` | Error (see `error_code`) | — |

**Production recommendation:** use [webhook subscriptions](#webhook-subscriptions) instead of polling for anchor completion — Flare block confirmations can take up to 5 minutes under congestion.

---

## Lightweight Receipt Status

**`GET /v1/iso/receipts/{receipt_id}/status`**

Returns only the status fields. Use this instead of the full receipt endpoint when polling for pipeline completion.

```json
{
  "id": "550e8400-...",
  "status": "anchored",
  "bundle_hash": "0xabc123...",
  "flare_txid": "0xdef456...",
  "anchored_at": "2024-01-01T00:01:30Z",
  "updated_at": "2024-01-01T00:01:30Z"
}
```

---

## Webhook Subscriptions

Register a URL to receive push notifications instead of polling. Webhooks are **HMAC-SHA256 signed** and retried up to 3 times (5 s → 30 s → 120 s backoff).

### Register a webhook

```http
POST /v1/webhooks
X-API-Key: your-key
Content-Type: application/json

{
  "url": "https://your-agent.example.com/webhook",
  "events": ["receipt.anchored", "receipt.failed"],
  "description": "My agent webhook"
}
```

Response includes the `secret` — store it securely, it is only returned at creation.

### Event topics

| Topic | When |
|-------|------|
| `receipt.pending` | Receipt accepted and queued |
| `receipt.anchored` | Evidence anchored on Flare (terminal success) |
| `receipt.failed` | Processing or anchoring failed (terminal failure) |
| `agent.anchored` | Agent-initiated anchor confirmed |
| `*` | All events |

### Payload shape

```json
{
  "event": "receipt.anchored",
  "receipt_id": "550e8400-...",
  "status": "anchored",
  "reference": "invoice:INV-2024-001",
  "bundle_hash": "0xabc123...",
  "flare_txid": "0xdef456...",
  "xml_url": "https://api/files/.../pain001.xml",
  "bundle_url": "https://api/files/.../evidence.zip",
  "created_at": "2024-01-01T00:00:00Z",
  "anchored_at": "2024-01-01T00:01:30Z",
  "metadata": { "task_id": "task-xyz" },
  "tags": ["batch-1"]
}
```

### Verifying signatures

```python
import hashlib, hmac

def verify_webhook(body: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)

# In your handler:
body = await request.body()
sig = request.headers["X-ISO-Signature-256"]
assert verify_webhook(body, sig, YOUR_WEBHOOK_SECRET)
```

### Test a webhook

```http
POST /v1/webhooks/{id}/test
```

Fires a synthetic `webhook.test` event so you can verify your endpoint is reachable.

---

## Receipt Metadata and Tags

Attach agent-specific context to receipts at creation time. Both fields are carried through the pipeline and included in webhook payloads.

```json
{
  "tip_tx_hash": "0xabc...",
  ...,
  "metadata": {
    "task_id": "task-xyz-123",
    "workflow": "monthly-reconciliation",
    "initiated_by": "agent-1",
    "correlation_id": "corr-456"
  },
  "tags": ["batch-1", "high-priority", "fx-enriched"]
}
```

### Filtering by tags

```http
GET /v1/receipts?tags=batch-1,high-priority
```

Returns receipts that contain **all** listed tags.

---

## Cursor-Based Pagination

Offset-based pagination (`page`/`page_size`) is unreliable for agents processing live data — new receipts arriving between pages cause skips or duplicates.

Use cursor-based pagination instead:

```http
GET /v1/receipts?page_size=50
```

Response:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "next_cursor": "eyJjcmVhdGVkX2F0IjogIjIwMjQtMDEtMDFUMDA6MDA6MDBaIiwgImlkIjogIjU1MGU4NDAwIn0="
}
```

Follow-up request:
```http
GET /v1/receipts?cursor=eyJjcmVhdGVkX2F0Ijoi...&page_size=50
```

The cursor encodes a `(created_at, id)` keyset position. It remains stable under concurrent inserts and does not skip rows.

---

## Rate Limit Headers

Every response includes:

| Header | Meaning |
|--------|---------|
| `X-RateLimit-Limit` | Requests allowed per window |
| `X-RateLimit-Remaining` | Requests left in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

When the limit is exceeded, you receive `429 Too Many Requests` with a `Retry-After` header.

### Tiers

| Caller | Limit |
|--------|-------|
| Unauthenticated | 30 req / 60 s |
| API key | 200 req / 60 s |
| Admin key | 1000 req / 60 s |

```python
import time

def request_with_backoff(client, *args, **kwargs):
    resp = client.request(*args, **kwargs)
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        time.sleep(retry_after)
        return client.request(*args, **kwargs)
    return resp
```

---

## Flare AI Skills Integration

This middleware embeds the [Flare AI Skills](https://github.com/flare-foundation/flare-ai-skills) knowledge base, exposing three Flare-specific endpoints for agents.

### Live FTSO Price Feeds

**`GET /v1/flare/feeds`** — All available feeds  
**`GET /v1/flare/feeds/{symbol}`** — Single feed (e.g. `FLR%2FUSD`)

```json
{
  "feeds": [
    {
      "symbol": "FLR/USD",
      "price": "0.02150",
      "timestamp": 1706000000,
      "age_seconds": 45.2,
      "feed_id_hex": "01464c522f555344000000000000000000000000000000",
      "source": "ftso_v2"
    },
    ...
  ],
  "update_frequency_seconds": 90,
  "registry_address": "0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019",
  "network": "flare"
}
```

Use `price` for FX enrichment in ISO 20022 messages. Prices are sourced from Flare FTSO v2 — the same oracle injected into payment evidence bundles.

### FDC Attestation Helper

**`POST /v1/flare/fdc/prepare-attestation`**

Prepares the Flare Data Connector request body for Merkle-proof-backed transaction verification. Stronger than raw Transfer-event checking.

```json
{
  "tx_hash": "0xabc123...",
  "chain": "flare",
  "required_confirmations": 6,
  "list_events": true
}
```

Response:
```json
{
  "attestation_type": "EVMTransaction",
  "request_body": {
    "transactionHash": "0xabc123...",
    "requiredConfirmations": "6",
    "provideInput": false,
    "listEvents": true,
    "logIndices": []
  },
  "verifier_url": "https://fdc-verifiers-testnet.aflabs.net/verifier/flr/EVMTransaction/prepareRequest",
  "da_layer_url": "https://da-layer-testnet.aflabs.net/api/v1/fdc/proof-by-request-round-raw",
  "note": "POST request_body to verifier_url with header X-apikey: <your-key>..."
}
```

**FDC flow:**
1. Call this endpoint → get `request_body` and URLs
2. POST to `verifier_url` with `X-apikey: <key>` → get `votingRoundId` + `requestBytes`
3. POST `{votingRoundId, requestBytes}` to `da_layer_url` → get Merkle proof
4. Submit proof to `IFdcVerification.verifyEVMTransaction()` on Flare for trustless on-chain verification

For testnet: use API key `00000000-0000-0000-0000-000000000000`.

### Natural Language Flare Explain

**`POST /v1/flare/explain`**

Ask any question about Flare protocol using the embedded Flare AI Skills knowledge.

```json
{
  "question": "How do I verify a USDC payment using FDC attestation?",
  "context": "tx hash 0xabc123 on Base"
}
```

Covers: FTSO v2, FDC attestation types, FAssets (FXRP/FBTC/FDOGE), Smart Accounts (XRPL bridge), Flare governance, and developer tooling.

Requires `OPENAI_API_KEY` (or compatible AI provider) to be configured.

---

## Environment Variables

New variables added for agentic features:

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `IDEMPOTENCY_ENABLED` | `true` | Enable/disable idempotency key middleware |
| `FDC_VERIFIER_URL` | testnet URL | FDC verifier API base URL |
| `FDC_DA_LAYER_URL` | testnet URL | FDC DA layer base URL for proof retrieval |
| `FDC_API_KEY` | `null` | X-apikey for FDC verifier (testnet: all-zeros UUID) |

Existing variables that affect agentic features:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Required for idempotency, rate limiting, and webhook retry queue |
| `PUBLIC_BASE_URL` | `null` | Used to build absolute URLs in webhook payloads |
| `FTSO_ENABLED` | `true` | Enable FTSO price feeds |
| `OPENAI_API_KEY` | `null` | Required for `/v1/flare/explain` |

---

## Complete Agent Integration Example

```typescript
// TypeScript agent using this middleware
import axios from "axios";

const API = axios.create({
  baseURL: "https://your-middleware.example.com",
  headers: { "X-API-Key": process.env.MIDDLEWARE_API_KEY },
});

// Step 0: Register webhook on startup (idempotent via Idempotency-Key)
await API.post("/v1/webhooks", {
  url: "https://my-agent.example.com/webhook",
  events: ["receipt.anchored", "receipt.failed"],
}, { headers: { "Idempotency-Key": "startup-webhook-v1" } });

// Step 1: Record payment (safe to retry)
const { data } = await API.post("/v1/iso/record-tip", {
  tip_tx_hash: txHash,
  chain: "flare",
  amount: "500.00",
  currency: "FLR",
  sender_wallet: sender,
  receiver_wallet: receiver,
  reference: `invoice:${invoiceId}`,
  metadata: { invoiceId, agentId: "agent-1" },
  tags: ["automated"],
}, { headers: { "Idempotency-Key": `record-${invoiceId}` } });

const { operation_id } = data;

// Step 2: Poll until terminal state
let status = "pending";
while (!["anchored", "failed"].includes(status)) {
  await new Promise(r => setTimeout(r, 3000));
  const op = await API.get(`/v1/operations/${operation_id}`);
  status = op.data.status;
  // Handle X-RateLimit-Remaining to avoid 429s
  const remaining = parseInt(op.headers["x-ratelimit-remaining"] ?? "100");
  if (remaining < 10) await new Promise(r => setTimeout(r, 5000));
}

// OR use the webhook handler instead:
// app.post("/webhook", (req, res) => {
//   verifySignature(req.body, req.headers["x-iso-signature-256"], SECRET);
//   if (req.body.event === "receipt.anchored") handleSuccess(req.body);
// });
```
