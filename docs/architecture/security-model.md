# Architecture: Security Model

## Authentication

ProofRails uses API key authentication. Keys are stored as SHA-256 hashes — the original key is shown once at creation and never retrievable again.

Key roles:

| Role | Access |
|------|--------|
| `admin` | All projects, analytics, config |
| `project_admin` | Own project, agent management, anchoring |
| `project` | Read own receipts, create receipts |

Public (unauthenticated) access is limited to health check and OpenAPI schema.

## Multi-tenancy

All data-access endpoints filter by `project_id` derived from the API key. Admin keys can use `scope=all` on list endpoints.

## x402 payment security

- In production (`X402_MOCK_PAYMENTS` unset or `false`): the backend queries the on-chain transaction, verifies the USDC contract address, recipient, and amount. Reused tx hashes are rejected.
- Replay protection: `X402Payment.tx_hash` has a unique constraint. Submitting the same tx hash twice returns 400.
- Amount validation: payments below the configured price are rejected.

## Private key handling (known weakness)

The `anchor_private_key_encrypted` field stores a base64-encoded key. This is obfuscation, not encryption. It protects against casual inspection but not against database compromise.

Mitigation:
- Use `ANCHOR_PRIVATE_KEY` server environment variable instead.
- Restrict database access to the application process.
- Use dedicated low-value wallets for anchoring (anchoring costs gas only, no value transferred).

This is documented in [Known Limitations](../KNOWN_LIMITATIONS.md) as a P2 item for future work.

## Bundle integrity

Evidence bundles are tamper-evident but not encrypted. Anyone with the bundle can read the ISO XML. The on-chain hash proves the bundle has not changed since anchoring but does not prevent disclosure.

If confidentiality is required:
- Store bundles with access-controlled storage (pre-signed URLs, private S3).
- The bundle URL in the receipt can be a time-limited signed URL.

## Rate limiting and idempotency

Rate limiting is configurable via `RATE_LIMIT_ENABLED` and `RATE_LIMIT_REQUESTS_PER_MINUTE`.

Idempotency keys prevent duplicate receipts on network retries. Configure via `IDEMPOTENCY_ENABLED`.

## CORS

CORS is configured in `app/api/app_factory.py`. In development, `*` is allowed. For production, set `CORS_ORIGINS` to specific frontend origins.

## Webhook security

Webhooks are signed with HMAC-SHA256 using a per-subscription secret. The secret is shown once at subscription creation. Verify the `X-Signature` header in your webhook handler.
