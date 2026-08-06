# ProofRails v2.2 Release Checklist

**Branch:** `agentic`  
**Last updated:** 2026-04-30

Mark each item as you verify it. Items marked ❌ are blocking for production merge.
Items marked ⚠️ are known limitations documented in KNOWN_LIMITATIONS.md.

---

## Automated checks

| Check | Command | Status |
|---|---|---|
| Python unit tests | `pytest -q -m "unit or not network"` | Run before merging |
| Alembic migration check | `alembic upgrade head` | Run before merging |
| TypeScript SDK build | `cd packages/sdk && npm run build` | Run before merging |
| Agent TypeScript build | `cd agents/iso-x402-agent && npm run build` | Run before merging |
| Next.js web build | `cd web-alt && npm run build` | Run before merging |

---

## Manual verification checklist

### Local API

- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET /v1/health` returns `{"status": "healthy"}`
- [ ] `GET /docs` renders OpenAPI UI with all expected endpoints
- [ ] All agent anchoring endpoints appear in `/openapi.json`
- [ ] All x402 premium endpoints appear in `/openapi.json`

### Core receipt flow

- [ ] `POST /v1/iso/record-tip` creates a receipt
- [ ] `GET /v1/iso/receipts/{id}` returns the receipt
- [ ] `GET /v1/iso/receipts/{id}/status` returns lightweight status
- [ ] `GET /v1/operations/{id}` returns operation status
- [ ] Webhook fires after receipt is anchored (requires Redis + test subscriber)

### Project and auth

- [ ] Project registration via SIWE works
- [ ] API key creation and revocation works
- [ ] `/api/proxy` in web-alt forwards correctly with project API key

### Agent CRUD

- [ ] `POST /v1/agents` creates an agent
- [ ] `GET /v1/agents` lists agents
- [ ] `GET /v1/agents/{id}` returns agent details
- [ ] `PUT /v1/agents/{id}` updates agent
- [ ] `DELETE /v1/agents/{id}` deletes agent

### Agent anchoring

- [ ] `GET /v1/agents/{id}/anchoring-config` returns defaults (all false, null wallet)
- [ ] `PUT /v1/agents/{id}/anchoring-config` persists boolean values correctly
- [ ] `POST /v1/agents/{id}/anchor-data` returns deterministic hash for same input
- [ ] `POST /v1/agents/{id}/anchor-data` with `submit_onchain=false` stays in `pending`
- [ ] `POST /v1/agents/{id}/anchor-data` with `submit_onchain=true` requires ANCHOR_PRIVATE_KEY
- [ ] `GET /v1/agents/{id}/anchors` lists anchors

### x402 payment gating

- [ ] `POST /v1/x402/premium/verify-bundle` without payment returns HTTP 402
- [ ] HTTP 402 response body contains `accepted` array with USDC and FLR options
- [ ] With `X402_MOCK_PAYMENTS=true`, any X-PAYMENT header bypasses verification
- [ ] With `X402_MOCK_PAYMENTS=false` (production), random/fake tx hash returns 403
- [ ] `POST /v1/x402/premium/generate-statement` with valid date returns receipt count
- [ ] `POST /v1/x402/premium/refund` accepts `original_receipt_id` (not `receipt_id`)

### XMTP agent

- [ ] `cd agents/iso-x402-agent && npm run build` compiles without errors
- [ ] Agent starts with `npm start` (requires XMTP env + wallet key)
- [ ] `help` command returns available commands including status, anchor, list anchors
- [ ] `status <receipt_id>` returns receipt status via `/v1/iso/receipts/{id}/status`
- [ ] `anchor {"key":"value"}` returns deterministic hash
- [ ] `list anchors` lists recent anchors for configured AGENT_ID
- [ ] `verify anchor <hash>` checks anchor status
- [ ] Paid commands (`verify`, `statement`, `refund`) return 402 when wallet has no USDC
- [ ] `X402_MOCK_PAYMENTS=true` allows paid commands in dev without real USDC

### Flare-native

- [ ] `GET /v1/flare/feeds` returns current prices when `FTSO_ENABLED=true`
- [ ] `GET /v1/flare/feeds/FLR%2FUSD` returns single feed
- [ ] `POST /v1/flare/fdc/prepare-attestation` returns verifier request body
- [ ] `POST /v1/flare/explain` returns a Flare protocol answer (requires OpenAI key)

### UI (web-alt)

- [ ] `cd web-alt && npm run dev` starts without errors
- [ ] Dashboard loads receipts
- [ ] Agent list page loads
- [ ] Anchoring config loads when selecting an agent
- [ ] Anchoring config can be saved
- [ ] Manual anchor-data form submits successfully

---

## Known gaps (not blocking — documented in KNOWN_LIMITATIONS.md)

- ⚠️ `generate-statement` returns receipt count but does not return the XML body as a download
- ⚠️ `anchor-data` with `submit_onchain=true` requires platform `ANCHOR_PRIVATE_KEY` in env; per-agent private key storage is not recommended for production
- ⚠️ Web-alt UI does not yet show full anchor history with explorer links
- ⚠️ FDC attestation helper constructs the request body but does not submit to the DA layer
- ⚠️ fAssets and Smart Accounts Flare integrations are proposed, not implemented

---

*Update this file as items are verified. Do not merge to main until all non-⚠️ items are checked.*
