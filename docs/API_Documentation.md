# API Documentation

Complete reference for the ISO 20022 Payments Middleware REST API.

**Base URL**: `http://localhost:8000` (default)

---

## Authentication

The API supports two authentication methods:

### API Key

Pass an API key via the `X-API-Key` header. Keys are SHA-256 hashed before storage and scoped to a project.

```
X-API-Key: your-api-key-here
```

Roles: `admin`, `project_admin`, `project`.

### Sign-In With Ethereum (SIWE)

EIP-4361 message + EIP-191 signature, used by the web UI. The flow:

1. `GET /v1/auth/nonce` → returns a one-time nonce and expected domain
2. Sign an EIP-4361 message with the nonce using your wallet
3. `POST /v1/auth/siwe-verify` with the signed message

---

## Health

### `GET /v1/health`

Returns service health including database and Redis status.

**Response:**

```json
{
  "status": "ok",
  "ts": "2026-01-20T20:00:00.000000",
  "env": "dev",
  "deps": {
    "db": { "ok": true, "detail": "ok" },
    "redis": { "ok": true, "detail": "ok" }
  }
}
```

`status` is `"ok"` when all dependencies are healthy, `"degraded"` otherwise.

### `GET /v1/ping`

Plain text health check. Returns `pong`.

---

## Receipts

### `POST /v1/iso/record-tip`

Record a blockchain transaction and start ISO 20022 processing. This is the primary write endpoint — it creates a receipt, enqueues it for compliance checks, ISO message generation, evidence bundling, and on-chain anchoring.

**Auth:** Required (API key or SIWE).

**Request:**

```json
{
  "tip_tx_hash": "0xabc123...",
  "chain": "flare",
  "amount": "100.50",
  "currency": "FLR",
  "sender_wallet": "0xSender...",
  "receiver_wallet": "0xReceiver...",
  "reference": "invoice-2026-001",
  "callback_url": "https://your-app.com/webhook"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tip_tx_hash` | string | Yes | Blockchain transaction hash |
| `chain` | string | Yes | EVM chain name (e.g. `flare`, `ethereum`, `base`) |
| `amount` | decimal | Yes | Transaction amount |
| `currency` | string | Yes | Currency code (e.g. `FLR`, `ETH`, `USDC`) |
| `sender_wallet` | string | Yes | Sender wallet address (0x...) |
| `receiver_wallet` | string | Yes | Receiver wallet address (0x...) |
| `reference` | string | Yes | Unique external reference |
| `callback_url` | string | No | Webhook URL for status notifications |

**Response (201):**

```json
{
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

Idempotent: if a receipt already exists for the same `chain` + `tip_tx_hash` or the same `reference`, the existing receipt is returned.

### `GET /v1/receipts`

List receipts with pagination and filters.

**Auth:** Required when any API keys exist in the system.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | Filter: `pending`, `awaiting_anchor`, `anchored`, `failed` |
| `chain` | string | — | Filter by chain name |
| `reference` | string | — | Filter by reference |
| `since` | string | — | ISO date, receipts created on or after |
| `until` | string | — | ISO date, receipts created on or before |
| `scope` | string | `mine` | `mine` (project-scoped) or `all` (admin only) |
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "550e8400-...",
      "status": "anchored",
      "amount": "100.50",
      "currency": "FLR",
      "chain": "flare",
      "reference": "invoice-2026-001",
      "created_at": "2026-01-20T20:00:00Z",
      "anchored_at": "2026-01-20T20:01:30Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### `GET /v1/iso/receipts/{receipt_id}`

Get full details for a single receipt.

**Response:**

```json
{
  "id": "550e8400-...",
  "status": "anchored",
  "bundle_hash": "0x1234...",
  "flare_txid": "0xabcd...",
  "xml_url": "/files/550e8400-.../pain001.xml",
  "bundle_url": "/files/550e8400-.../evidence.zip",
  "created_at": "2026-01-20T20:00:00Z",
  "anchored_at": "2026-01-20T20:01:30Z"
}
```

### `GET /v1/iso/events/{receipt_id}`

Server-Sent Events (SSE) stream for real-time receipt status updates. Connect with an `EventSource` or SSE client to receive live status transitions (pending → bundling → awaiting_anchor → anchored).

**Content-Type:** `text/event-stream`

---

## Verification

### `POST /v1/iso/verify`

Verify an evidence bundle against on-chain anchoring records.

**Request:**

```json
{
  "bundle_url": "https://ipfs.io/ipfs/Qm...",
  "bundle_hash": "0x1234..."
}
```

Provide either `bundle_url` or `bundle_hash` (or both). When a URL is given, the bundle is fetched, its SHA-256 hash computed, and the hash is looked up on-chain.

**Response:**

```json
{
  "matches_onchain": true,
  "bundle_hash": "0x1234...",
  "flare_txid": "0xabcd...",
  "anchored_at": "2026-01-20T20:01:30Z",
  "errors": []
}
```

### `POST /v1/iso/verify-cid`

Verify by content identifier (IPFS or Arweave).

**Request:**

```json
{
  "cid": "QmXyz...",
  "store": "ipfs",
  "receipt_id": "optional-receipt-id"
}
```

`store` is auto-detected from the CID format if omitted. If `receipt_id` is provided, the endpoint also checks for a Verifiable Credential (`vc.json`) in the bundle.

---

## ISO Messages

### `GET /v1/iso/messages/{receipt_id}`

List generated ISO 20022 XML artifacts for a receipt.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Filter by message type (e.g. `pain.001`, `pacs.008`) |

**Response:**

```json
[
  {
    "type": "pain.001",
    "url": "/files/550e8400-.../pain001.xml",
    "sha256": "0xabcd...",
    "created_at": "2026-01-20T20:00:05Z"
  }
]
```

### FI-to-FI Message Generation

These endpoints generate institution-level ISO messages for an existing receipt. All require authentication.

#### `POST /v1/iso/camt056/{receipt_id}`

Generate a **camt.056** FI-to-FI Payment Cancellation Request.

#### `POST /v1/iso/camt029/{receipt_id}`

Generate a **camt.029** Resolution of Investigation.

#### `POST /v1/iso/pacs007/{receipt_id}`

Generate a **pacs.007** FI-to-FI Payment Reversal.

#### `POST /v1/iso/pacs009/{receipt_id}`

Generate a **pacs.009** Financial Institution Credit Transfer.

**Request (all four endpoints):**

```json
{
  "reason_code": "CUST",
  "resolution_code": "APPR"
}
```

Both fields are optional. Common reason codes: `CUST` (customer request), `TECH` (technical), `DUPL` (duplicate), `FRAD` (fraud).

**Response:**

```json
{
  "message_id": "MSG-2026-01-20-001",
  "type": "camt.056",
  "receipt_id": "550e8400-...",
  "url": "/files/550e8400-.../camt056.xml"
}
```

---

## Refunds

### `POST /v1/iso/refund`

Initiate a refund/return for an anchored receipt. Creates a new receipt with reversed sender/receiver, generates a pacs.004 payment return message, and enqueues it for bundling and anchoring.

**Auth:** Required.

**Request:**

```json
{
  "original_receipt_id": "550e8400-...",
  "reason_code": "CUST"
}
```

The original receipt must be in `anchored` status.

**Response:**

```json
{
  "refund_receipt_id": "660f9500-...",
  "status": "pending"
}
```

---

## Anchoring

### `GET /v1/anchors/{receipt_id}`

Get per-chain anchor transactions for a receipt.

**Response:**

```json
[
  {
    "chain": "flare",
    "txid": "0xabcd...",
    "anchored_at": "2026-01-20T20:01:30Z"
  }
]
```

### `POST /v1/iso/confirm-anchor`

Confirm an on-chain anchor for tenant/self-hosted mode. When your project is configured with `execution_mode: "tenant"`, you anchor the bundle hash on-chain yourself and then call this endpoint so the middleware can validate the transaction logs.

**Auth:** Required. Must have access to the receipt's project.

**Request:**

```json
{
  "receipt_id": "550e8400-...",
  "chain": "flare",
  "flare_txid": "0xabcd..."
}
```

The middleware fetches the transaction receipt from the chain, verifies the `EvidenceAnchored` event matches the expected bundle hash and contract address, and — if valid — marks the receipt as `anchored`.

**Response:**

```json
{
  "receipt_id": "550e8400-...",
  "status": "anchored",
  "flare_txid": "0xabcd...",
  "anchored_at": "2026-01-20T20:01:30Z"
}
```

### `POST /v1/debug/anchor`

Directly anchor a bundle hash on-chain (admin/debug use).

**Auth:** Required.

**Request:**

```json
{
  "bundle_hash": "0x1234567890abcdef..."
}
```

**Response:**

```json
{
  "flare_txid": "0xabcd...",
  "block_number": 12345678
}
```

---

## Projects

### `POST /v1/projects/register`

Register a new project using SIWE authentication. Returns the project details and a one-time API key.

**Request:**

```json
{
  "name": "My Payment Project",
  "message": "<EIP-4361 SIWE message>",
  "signature": "<EIP-191 signature>"
}
```

**Response:**

```json
{
  "project": {
    "id": "770a6600-...",
    "name": "My Payment Project",
    "owner_wallet": "0xOwner...",
    "created_at": "2026-01-20T20:00:00Z"
  },
  "api_key": "returned-only-once-save-it"
}
```

### `GET /v1/projects`

List projects accessible to the current principal.

**Auth:** Required.

### `GET /v1/projects/{project_id}/config`

Get project anchoring configuration.

**Auth:** Required (project access).

**Response:**

```json
{
  "anchoring": {
    "execution_mode": "platform",
    "chains": [
      {
        "name": "flare",
        "contract": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
        "rpc_url": null,
        "explorer_base_url": "https://flarescan.com"
      }
    ]
  }
}
```

### `PUT /v1/projects/{project_id}/config`

Update project anchoring configuration.

**Auth:** Required (project admin).

---

## Authentication & API Keys

### `GET /v1/auth/nonce`

Get a one-time nonce for SIWE authentication.

**Response:**

```json
{
  "nonce": "unique-uuid",
  "domain": "localhost"
}
```

### `POST /v1/auth/siwe-verify`

Verify a SIWE message and establish authentication.

**Request:**

```json
{
  "message": "<EIP-4361 message string>",
  "signature": "<EIP-191 signature>"
}
```

### `GET /v1/auth/me`

Return the current principal's role, project ID, and admin status.

**Auth:** Required.

**Response:**

```json
{
  "role": "project_admin",
  "project_id": "770a6600-...",
  "is_admin": false
}
```

### `POST /v1/auth/api-keys`

Create a new API key for the current project.

**Auth:** Required.

**Request:**

```json
{
  "label": "CI Pipeline Key"
}
```

The raw API key is returned in the `X-API-Key` response header — this is the only time the unhashed key is available.

### `GET /v1/auth/api-keys`

List API keys (hashed; the raw key is never retrievable).

### `DELETE /v1/auth/api-keys/{id}`

Revoke an API key.

### `GET /v1/auth/linked-wallets`

List SIWE-linked wallet addresses.

### `DELETE /v1/auth/linked-wallets/{address}`

Unlink a wallet address.

---

## Agents

### `POST /v1/agents`

Register a new autonomous agent.

**Auth:** Required.

**Request:**

```json
{
  "name": "Payment Bot",
  "wallet_address": "0xAgent...",
  "xmtp_address": "0xXmtp...",
  "pricing_rules": {
    "verify": "0.001",
    "statement": "0.005"
  }
}
```

### `GET /v1/agents`

List agents for the current project.

### `GET /v1/agents/{agent_id}`

Get agent details.

### `PUT /v1/agents/{agent_id}`

Update agent configuration.

### `DELETE /v1/agents/{agent_id}`

Delete an agent.

### `GET /v1/agents/{agent_id}/stats`

Get agent usage statistics (payment counts, revenue, etc.).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days to look back |

### `POST /v1/agents/{agent_id}/test`

Test an agent's configuration (connectivity check).

### `PUT /v1/agents/{agent_id}/ai-config`

Update AI configuration for an agent.

**Request:**

```json
{
  "ai_mode": "shared",
  "ai_system_prompt": "You are a payment assistant...",
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini"
}
```

`ai_mode` values: `simple` (no AI, exact command matching), `shared` (uses system AI — free), `custom` (your own API key).

### `POST /v1/agents/{agent_id}/download-template`

Download a deployment template for the agent.

---

## Agent Anchoring

### `POST /v1/agents/{agent_id}/anchor`

Manually trigger anchoring for an agent.

**Auth:** Required.

**Request:**

```json
{
  "bundle_hash": "0x1234...",
  "receipt_id": "optional-receipt-id"
}
```

**Response:**

```json
{
  "anchor_id": "880b7700-...",
  "bundle_hash": "0x1234...",
  "status": "pending",
  "message": "Anchoring initiated"
}
```

### `GET /v1/agents/{agent_id}/anchors`

List anchoring history for an agent.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days to look back |
| `status` | string | — | Filter: `pending`, `confirmed`, `failed` |

### `PUT /v1/agents/{agent_id}/anchoring-config`

Update agent anchoring configuration (auto-anchor toggle, payment-triggered anchoring, dedicated wallet).

**Request:**

```json
{
  "auto_anchor_enabled": true,
  "anchor_on_payment": true,
  "anchor_wallet": "0xDedicated..."
}
```

### `GET /v1/agents/{agent_id}/activity-unified`

Get a unified activity feed combining anchoring events, payments, and agent actions.

---

## x402 Micropayments

### `GET /v1/x402/pricing`

Get all payment-gated endpoint pricing.

**Response:**

```json
[
  {
    "path": "/v1/x402/premium/verify-bundle",
    "price": "0.001",
    "currency": "USDC",
    "recipient": "0x0690..."
  }
]
```

### `POST /v1/x402/pricing`

Update endpoint pricing (admin only).

### `GET /v1/x402/payments`

List recent x402 payments.

**Auth:** Required.

### Premium Endpoints (x402-Gated)

These endpoints require a USDC micropayment via the `X-PAYMENT` header. If no payment is provided, they return HTTP 402 with payment details. If payment is provided and verified on-chain, the request proceeds.

| Endpoint | Method | Price | Description |
|----------|--------|-------|-------------|
| `/v1/x402/premium/verify-bundle` | POST | 0.001 USDC | Verify an evidence bundle |
| `/v1/x402/premium/generate-statement` | POST | 0.005 USDC | Generate camt.052/camt.053 statement |
| `/v1/x402/premium/iso-message/{receipt_id}/{type}` | GET | 0.002 USDC | Get specific ISO message artifact |
| `/v1/x402/premium/fx-lookup` | POST | 0.001 USDC | FX rate lookup |
| `/v1/x402/premium/bulk-verify` | POST | 0.010 USDC | Bulk bundle verification |
| `/v1/x402/premium/refund` | POST | 0.003 USDC | Initiate a refund |

**402 Response (no payment provided):**

```json
{
  "amount": "0.001",
  "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  "reference": "x402:premium_verify_bundle:1706...",
  "currency": "USDC",
  "chain": "base"
}
```

Headers: `X-Payment-Required: true`, `X-Payment-Amount: 0.001`, `X-Payment-Currency: USDC`.

**X-PAYMENT header format (JSON):**

```json
{
  "tx_hash": "0xPaymentTxHash...",
  "amount": "0.001",
  "recipient": "0x0690...",
  "currency": "USDC",
  "chain": "base",
  "timestamp": "2026-01-20T20:00:00Z"
}
```

On successful verification, the response includes an `X-Payment-Response` header:

```json
{
  "verified": true,
  "tx_hash": "0xPaymentTxHash...",
  "amount": "0.001"
}
```

---

## Configuration

### `GET /v1/config`

Get organization-level configuration.

### `PUT /v1/config`

Update organization-level configuration.

**Auth:** Required.

---

## AI Assistant

### `POST /v1/ai/assist`

Scoped AI assistant for natural-language queries about receipts, verification, and SDK usage. The AI's access is scoped to the caller's project — a project API key cannot use AI to read another project's receipts.

**Auth:** Required.

**Request:**

```json
{
  "message": "Show me my recent anchored receipts"
}
```

### `GET /v1/ai/status`

Get AI provider configuration status.

**Response:**

```json
{
  "enabled": true,
  "provider": "openai",
  "model": "gpt-4o-mini",
  "has_api_key": true,
  "features": {
    "scope_enforcement": true,
    "receipt_tools": true,
    "sdk_help": true,
    "verification": true
  }
}
```

### `POST /v1/ai/parse-command`

Parse a natural language command into a structured action (used by XMTP agents).

**Request:**

```json
{
  "message": "show me 5 receipts",
  "system_prompt": "optional custom prompt"
}
```

**Response:**

```json
{
  "success": true,
  "parsed_command": {
    "action": "list",
    "args": { "limit": 5 }
  },
  "original_message": "show me 5 receipts"
}
```

---

## SDK Scaffold

### `POST /v1/sdk/build`

Build a quick-start SDK scaffold as a downloadable ZIP. Supports TypeScript and Python.

**Request:**

```json
{
  "lang": "ts",
  "base_url": "http://localhost:8000",
  "auth": "api_key",
  "packaging": "npm",
  "families": ["pain", "pacs"]
}
```

---

## Static Files & UI

| Path | Description |
|------|-------------|
| `/files/{receipt_id}/` | Generated artifacts (XML, ZIP, JSON) |
| `/ui/receipt.html?rid=...` | Receipt viewer UI |
| `/receipt/{receipt_id}` | Redirect to receipt viewer |
| `/embed/receipt?rid=...&theme=...` | Embeddable receipt widget |

---

## Error Handling

All error responses follow a consistent format:

```json
{
  "detail": "error_code_or_message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid input, missing fields) |
| 401 | Unauthorized (missing or invalid API key / SIWE session) |
| 402 | Payment Required (x402 — payment needed) |
| 403 | Forbidden (insufficient permissions, wrong project) |
| 404 | Not found |
| 422 | Validation error (invalid JSON, schema mismatch) |
| 500 | Internal server error |
| 503 | Service unavailable (blockchain RPC down) |

---

## Receipt Status Lifecycle

```
pending → [compliance + ISO generation + bundling] → awaiting_anchor → [on-chain tx] → anchored
                                                                    ↘ failed (on timeout or revert)
```

| Status | Description |
|--------|-------------|
| `pending` | Receipt created, queued for processing |
| `awaiting_anchor` | Evidence bundle generated, waiting for on-chain anchor |
| `anchored` | Bundle hash confirmed on-chain |
| `failed` | Processing or anchoring failed |

---

## Supported ISO 20022 Message Types

| Type | Name | Generated When |
|------|------|----------------|
| pain.001 | Customer Credit Transfer Initiation | Receipt creation |
| pain.002 | Customer Payment Status Report | Status updates |
| pain.007 | Customer Payment Reversal | Refund processing |
| pain.008 | Customer Direct Debit Initiation | Direct debit flows |
| pacs.002 | FI-to-FI Payment Status Report | Anchoring confirmation |
| pacs.004 | Payment Return | Refund/return processing |
| pacs.007 | FI-to-FI Payment Reversal | Via `/v1/iso/pacs007/{rid}` |
| pacs.008 | FI-to-FI Customer Credit Transfer | Cross-institution transfers |
| pacs.009 | Financial Institution Credit Transfer | Via `/v1/iso/pacs009/{rid}` |
| camt.029 | Resolution of Investigation | Via `/v1/iso/camt029/{rid}` |
| camt.052 | Bank-to-Customer Account Report (intraday) | Statement generation |
| camt.053 | Bank-to-Customer Statement | Statement generation |
| camt.054 | Bank-to-Customer Debit/Credit Notification | Event notifications |
| camt.056 | FI-to-FI Payment Cancellation Request | Via `/v1/iso/camt056/{rid}` |
| remt.001 | Remittance Advice | Remittance processing |
