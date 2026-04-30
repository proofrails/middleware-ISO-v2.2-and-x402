# Known Limitations

**Branch:** `agentic` | **Updated:** 2026-04-30

---

## Backend

### generate-statement returns count, not XML download
`POST /v1/x402/premium/generate-statement` queries receipts and calls the camt.052/053
generator but returns the XML inline as a string field rather than as a file download.
For large datasets this may produce oversized responses. A future version should stream
the XML as `application/xml` with `Content-Disposition: attachment`.

### anchor-data private key handling
`PUT /v1/agents/{id}/anchoring-config` accepts `anchor_private_key` and stores it
base64-encoded. This is NOT encryption — it is encoding only. For production deployments
with multiple agents, use the platform `ANCHOR_PRIVATE_KEY` env var (loaded from a
secrets manager) and leave per-agent key storage blank. The per-agent key path exists
for self-hosted, single-tenant deployments only.

### FDC attestation helper does not submit
`POST /v1/flare/fdc/prepare-attestation` constructs the verifier request body but does
not submit it to the DA layer or wait for a Merkle proof. It is a request-builder, not
a full FDC integration. Full FDC verification flow (prepareRequest → DA layer → proof
retrieval → on-chain verify) is a proposed future feature.

### x402 payment replay protection
`X402PaymentVerifier` verifies that a transaction exists on-chain and matches amount +
recipient, but does not check whether the same `tx_hash` has been used for a previous
request to the same endpoint. A malicious client could replay a valid tx hash. Add a
`UNIQUE(tx_hash, endpoint)` DB constraint and rejection logic to close this gap.

### X402_MOCK_PAYMENTS reads env at import time
`x402_premium.py` reads `X402_MOCK_PAYMENTS` at module import. If the env var is set
after the module is loaded (e.g. via `monkeypatch` in tests without a module reload),
the mock flag will not be active. Tests that rely on monkeypatching must call
`importlib.reload(app.api.routes.x402_premium)` after setting the env var.

---

## XMTP Agent

### Anchor commands require AGENT_ID
The `anchor`, `list anchors`, and `verify anchor` XMTP commands require the `AGENT_ID`
env var to be set to a valid agent ID registered in the backend. Without it the
commands will return an empty string agent ID and the backend will return 404.

### AI command parsing for new commands
The NLP parser (`utils/parser.ts`) was not updated to recognise `anchor`, `status`,
`list anchors`, or `verify anchor` as intents. In `simple` AI mode these commands are
matched by exact string prefix. In `shared`/`custom` modes the LLM must be prompted to
recognise them. Add intent patterns to the parser for robust natural-language handling.

---

## UI

### Anchor history not displayed
The web-alt agent UI saves anchoring config but does not display anchor history or show
explorer links. `GET /v1/agents/{id}/anchors` is implemented on the backend but not
called from the frontend.

### agents/page.tsx bypasses /api/proxy
The agents page currently calls `NEXT_PUBLIC_API_BASE` directly from the browser. Other
pages use `/api/proxy` which injects the project API key server-side. This means agent
operations from the browser do not carry the project API key unless it is set as a
public env var, which exposes it to clients.

---

## Flare-native

### fAssets evidence flows — proposed only
ISO-style evidence records for FXRP/FBTC/FDOGE activity are a proposed integration.
No FAssets bridge event indexing or receipt generation exists yet.

### Smart Accounts / XRPL flows — proposed only
XRPL-to-Flare user flows via Smart Accounts are a proposed integration. No delegation
mapping or XRPL event listener exists yet.

### FTSO price at time of anchoring not stored
Receipts do not currently record the FLR/USD (or other) spot price at the moment of
anchoring. Adding an `fx_rate_at_anchor` field to the receipt model would make ISO
reporting more auditable.

---

## Testing

### Cursor pagination tested against SQLite only
SQLite timestamps have microsecond resolution but may produce duplicate `created_at`
values for records inserted in the same transaction during tests. The cursor keyset
`(created_at DESC, id DESC)` is fully correct in PostgreSQL. SQLite tests verify cursor
accessibility but not strict non-overlap guarantees.

### Live RPC tests excluded from CI
Tests marked `@pytest.mark.network` require a live Flare RPC, Base RPC, or XMTP
network. They are excluded from the default `pytest -q` run. Run them manually with
`pytest -m network` against a configured environment.
