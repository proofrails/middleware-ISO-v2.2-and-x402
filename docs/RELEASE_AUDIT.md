# ProofRails v2.2 Release Audit

**Branch:** `agentic`  
**Audited:** 2026-04-30  
**Auditor:** Release engineering review  
**Scope:** Full pre-release audit of middleware-ISO-v2.2-and-x402 agentic branch

---

## 1. Repository Structure

```
middleware-ISO-v2-x402_final/
├── .claude/settings.local.json          # Claude Code settings (local only)
├── .github/workflows/tests.yml          # CI: runs pytest on push/PR
├── .gitignore                           # Excludes .env, .keys, Downloads/, .next
├── .env.example                         # ✅ present
├── .env.production.example              # ✅ present
├── alembic/
│   └── versions/
│       ├── 8d23500035d7_init.py         # baseline: projects, receipts, anchors
│       ├── 5a8e64824892_add_x402.py     # x402_payments, agent_configs, protected_endpoints
│       ├── ca553b86c849_add_ai.py       # ai_mode, ai_provider, etc. on agent_configs
│       └── d8f9c3b21456_add_anchoring.py # agent_anchors, anchoring cols on agents/payments
├── app/
│   ├── models.py                        # ⚠️ MISSING 6 columns defined in migrations
│   ├── schemas.py                       # Pydantic schemas — missing agent/x402 schemas
│   ├── x402.py                          # require_payment decorator + X402PaymentVerifier
│   ├── api/routes/
│   │   ├── agent_anchoring.py           # ⚠️ Missing GET config, POST anchor-data endpoints
│   │   └── x402_premium.py             # ❌ Decorator order bug — payment gate never fires
├── agents/iso-x402-agent/src/x402/
│   └── client.ts                        # ❌ Mock payments, wrong endpoints, wrong payloads
├── docs/                                # 6 markdown files — no subdirectory structure
├── packages/
│   ├── sdk/                             # TypeScript SDK — missing agent/x402 methods
│   └── sdk-python/                      # Python SDK — missing agent methods
├── tests/
│   ├── test_agent_anchoring_smoke.py    # ❌ Uses external HTTP requests (requires live server)
│   ├── test_x402_smoke.py              # ❌ Uses external HTTP requests (requires live server)
│   └── test_agentic_features.py        # ✅ 52 tests, TestClient-based
├── web-alt/
│   ├── .env.local                       # ❌ Local env file checked in to repo
│   ├── tsconfig.tsbuildinfo             # ❌ Build artifact checked in (98.8 KB)
│   └── app/CPU-20260119T114549.377Z.cpuprofile.txt  # ❌ CPU profile checked in (9 MB)
└── README.md                            # ⚠️ Old clone URL, duplicate intro block
```

---

## 2. Broken Docs and Missing Files

| Link in README / Docs | Status | Note |
|---|---|---|
| `../API_Documentation.md` | ❌ Wrong path | File is at `docs/API_Documentation.md`, link uses `../` |
| `../docs/AGENT_ANCHORING.md` | ❌ Wrong path | Same issue with `../docs/` prefix |
| `../docs/X402_INTEGRATION.md` | ❌ Wrong path | Same |
| `../docs/AGENTS_GUIDE.md` | ❌ Wrong path | Same |
| Old clone URL | ❌ Wrong repo | README uses `github.com/alfre97x/middleware-ISO-and-x402` |
| `docs/` subdirectory structure | ❌ Missing | No `concepts/`, `guides/`, `api/`, `architecture/`, `examples/` |
| `docs/RELEASE_CHECKLIST.md` | ❌ Missing | Required by spec |
| `docs/KNOWN_LIMITATIONS.md` | ❌ Missing | Required by spec |
| `.claude/settings.json` | ❌ Missing | Flare AI Skills not configured |

The `docs/` files themselves exist and have substantial content. The problem is (a) incorrect relative paths in README links and (b) missing subdirectory structure and index.

---

## 3. Backend Endpoint Mismatches

### 3.1 Missing endpoints

| Expected endpoint | Status | Where referenced |
|---|---|---|
| `GET /v1/agents/{agent_id}/anchoring-config` | ❌ Not implemented | `test_agent_anchoring_smoke.py`, `docs/AGENT_ANCHORING.md` |
| `POST /v1/agents/{agent_id}/anchor-data` | ❌ Not implemented | `test_agent_anchoring_smoke.py`, `docs/AGENT_ANCHORING.md`, README |

### 3.2 Present but broken

| Endpoint | Bug |
|---|---|
| `POST /v1/x402/premium/verify-bundle` | Decorator order: `@require_payment` applied above `@router.post`, so FastAPI registers the unprotected function. Payment gate never fires in production. |
| `POST /v1/x402/premium/generate-statement` | Returns empty payload. `receipts = []` is hardcoded. Never queries database. |
| `POST /v1/x402/premium/verify-bundle` | Calls `await verify_impl(payload)` but `verify_impl` (imported from `routes/verify.py`) is a sync function. This will raise `TypeError` at runtime. |
| `POST /v1/agents/{agent_id}/anchor` | References `agent.anchor_wallet_address` and `agent.anchor_private_key_encrypted` — columns not defined in `app/models.py` → `AttributeError` at runtime. |
| `PUT /v1/agents/{agent_id}/anchoring-config` | Stores booleans as strings: `agent.auto_anchor_enabled = str(...).lower()`. Migration defines `Boolean` type. Will cause inconsistent comparisons. |
| `GET /v1/agents/{agent_id}/activity-unified` | References `p.anchor_txid` and `p.anchor_status` on `X402Payment` — columns not in model → `AttributeError`. |

---

## 4. Model / Migration Misalignment (Critical)

The Alembic migration `d8f9c3b21456_add_agent_anchoring.py` adds the following columns, but **none of them appear in `app/models.py`**:

### Missing on `AgentConfig`:
- `anchor_wallet_address` (String, nullable)
- `anchor_private_key_encrypted` (String, nullable)
- `auto_anchor_enabled` (Boolean, server_default=false)
- `anchor_on_payment` (Boolean, server_default=false)

### Missing on `X402Payment`:
- `anchor_txid` (String, nullable)
- `anchor_status` (String, nullable, indexed)

### Impact:
Any code path that reads or writes these attributes (`agent_anchoring.py`, `x402_premium.py`, `activity-unified`) will raise `AttributeError` at runtime. The database schema is correct after migrations; the Python ORM layer is incomplete.

### Additional model issue:
`X402Payment` has no `receipt_id` column, but `_perform_anchor()` in `agent_anchoring.py` (line 289) queries `X402Payment.filter_by(receipt_id=agent_anchor.receipt_id)`. This will raise `InvalidColumnError`.

---

## 5. x402 Payment Flow Issues

### 5.1 Decorator order bug (all premium endpoints)

In `app/api/routes/x402_premium.py`:
```python
# BROKEN — FastAPI registers the unprotected function:
@require_payment("0.001", X402_RECIPIENT, ...)
@router.post("/v1/x402/premium/verify-bundle")
async def premium_verify_bundle(request: Request, ...):
```
Python applies decorators bottom-up. `@router.post(...)` executes first, registering the raw `premium_verify_bundle` function with FastAPI. Then `@require_payment(...)` wraps the return value of `router.post(...)`, but FastAPI already stored a reference to the unprotected function. All six premium endpoints are affected.

**Fix:** Swap decorator order:
```python
@router.post("/v1/x402/premium/verify-bundle")
@require_payment("0.001", X402_RECIPIENT, ...)
async def premium_verify_bundle(request: Request, ...):
```

### 5.2 Mock payments in production

`agents/iso-x402-agent/src/x402/client.ts` generates a random transaction hash in `makePayment()`:
```typescript
const mockTxHash = `0x${Math.random().toString(16).slice(2)}...`;
```
There is no env-flag guard. In production, this mock hash will never verify against a real blockchain, causing every paid request to fail with `403 payment_verification_failed`. The code must be gated behind `X402_MOCK_PAYMENTS=true`.

### 5.3 `generate-statement` returns empty data

```python
receipts = []  # hardcoded — never queries database
xml = camt053.generate_camt053(date, receipts)
return {"type": "camt.053", "date": date, "count": 0}
```
This endpoint is payment-gated but does nothing useful. It is currently **not production-ready**.

### 5.4 `await verify_impl(payload)` on sync function

`verify` in `app/api/routes/verify.py` is a sync function decorated with `@router.post(...)`. Calling `await verify_impl(payload)` directly will raise `TypeError: object NoneType can't be used in 'await' expression`.

---

## 6. Agent Client/Backend Mismatches

In `agents/iso-x402-agent/src/x402/client.ts`:

| Issue | Current | Correct |
|---|---|---|
| Get single receipt | `GET /v1/receipts/${id}` | `GET /v1/iso/receipts/${id}` |
| List receipts response | Accesses `response.data` directly as array | Backend returns `{items:[...], total:..., page:..., next_cursor:...}` |
| Generate statement | Sends body `{date}` → treated as JSON body | `date` is a query parameter in FastAPI handler |
| Refund payload | `{receipt_id, reason, return_method}` | Schema is `{original_receipt_id, reason_code?}` |
| Payment implementation | Random mock hash, no real USDC transfer | Must use `ethers` v6 `JsonRpcProvider` + ERC-20 transfer with 6-decimal USDC |

---

## 7. Agent Commands: Docs vs. Implementation

`agents/iso-x402-agent/README.md` documents these commands:
`help`, `list`, `get`, `verify`, `statement`, `refund`, **`status`**, **`anchor`**, **`list anchors`**, **`verify anchor`**

`agents/iso-x402-agent/src/agent.ts` switch statement handles:
`help`, `list`, `get`, `verify`, `statement`, `refund`

**Missing handlers (bolded above):**
- `status` — no `handlers/status.ts`, no case in switch
- `anchor` — no `handlers/anchoring.ts`, no case in switch
- `list anchors` — same
- `verify anchor` — same

---

## 8. UI Issues

In `web-alt/app/agents/page.tsx`:
- Uses `process.env.NEXT_PUBLIC_API_BASE` directly instead of `/api/proxy`, bypassing server-side API key injection used everywhere else in the app
- Does not load existing anchoring config when mounting component (only saves, never fetches)
- No manual anchor-data UI

In `web-alt/components/agents/AgentAnchoring.tsx`:
- No form to submit arbitrary JSON data for hashing/anchoring (referenced in docs but not implemented)

---

## 9. SDK Inconsistencies

### TypeScript SDK (`packages/sdk/src/index.ts`)
Missing methods:
- `createAgent`, `listAgents`, `getAgent`, `updateAgent`, `deleteAgent`
- `getAgentAnchoringConfig`, `updateAgentAnchoringConfig`
- `anchorAgentData`, `listAgentAnchors`
- `listX402Payments`, `getX402Revenue`

### Python SDK (`packages/sdk-python/src/iso_middleware_sdk/client.py`)
Present methods are correct. Missing methods:
- All agent CRUD operations
- Agent anchoring operations
- x402 payment management

---

## 10. CI / Test Issues

### External HTTP tests

`tests/test_agent_anchoring_smoke.py` and `tests/test_x402_smoke.py` use `import requests` and call `http://127.0.0.1:8000` directly. These will fail in CI where no server is running. Pytest collects them without `@pytest.mark.network` or skip logic, so `pytest -q` fails unless a server is manually started.

### Missing pytest markers
No `pytest.ini` markers registered for `unit`, `integration`, `network`, `e2e`. CI runs everything without separation.

### Missing tests
- Agent CRUD via TestClient
- GET/PUT anchoring-config via TestClient
- POST anchor-data hash determinism
- x402 402 response without payment header
- x402 mock mode with `X402_MOCK_PAYMENTS=true`
- Docs internal link validity

### CI workflow gaps
`.github/workflows/tests.yml` runs only Python tests. Does not run:
- Alembic migration check (`alembic upgrade head`)
- TypeScript SDK build
- Next.js web build
- Agent TypeScript build
- Docs link check

---

## 11. Repo Hygiene Issues

| Item | Size | Action |
|---|---|---|
| `web-alt/.env.local` | — | Remove; contains local `NEXT_PUBLIC_API_BASE`. Should be `.env.local.example` |
| `web-alt/tsconfig.tsbuildinfo` | 98.8 KB | Remove; build artifact |
| `web-alt/app/CPU-20260119T114549.377Z.cpuprofile.txt` | 9 MB | Remove; profiling artifact |
| `test_agentic.db` | — | Remove; test SQLite DB left over from local test runs |
| `.gitignore` | — | Add `*.tsbuildinfo`, `*.cpuprofile.txt`, `web-alt/.env.local` |
| README clone URL | — | Fix: `github.com/alfre97x/middleware-ISO-and-x402` → `github.com/proofrails/middleware-ISO-v2.2-and-x402` |

---

## 12. Flare-Native Implementation Opportunities

| Feature | Status | What's needed |
|---|---|---|
| **FTSO v2 price feeds** | ✅ Implemented | `GET /v1/flare/feeds` + `/v1/flare/feeds/{symbol}` via `app/flare/ftso.py` |
| **FDC attestation prep** | ✅ Prototype | `POST /v1/flare/fdc/prepare-attestation` — constructs request body; does not submit |
| **Evidence hash anchoring on Flare EVM** | ✅ Implemented | `app/anchor.py` + Alembic migrations + ChainAnchor model |
| **FX rate enrichment in ISO records** | ✅ Implemented | `fx_providers.py` with FTSO provider path |
| **FDC payment verification** | 🔲 Proposed | Would verify payment existence on external chains before generating receipt |
| **fAssets evidence flows** | 🔲 Proposed | ISO-style records for FXRP/FBTC/FDOGE; needs FAssets bridge events |
| **Smart Accounts / XRPL flows** | 🔲 Proposed | XRPL-to-Flare user triggers; needs delegated account mapping |
| **Flare AI Skills** | 🔲 Not configured | `.claude/settings.json` not present; skills not referenced in IDE config |

---

## 13. Implementation Plan (Prioritised)

### P0 — Blockers (will cause runtime crashes)
1. Add missing columns to `app/models.py`: 4 on `AgentConfig`, 2 on `X402Payment`
2. Fix decorator order in `app/api/routes/x402_premium.py` (all 6 endpoints)
3. Fix `await verify_impl(payload)` → call sync function without await
4. Fix `X402Payment.filter_by(receipt_id=...)` — column does not exist

### P1 — Correctness (features claimed to work but don't)
5. Add `GET /v1/agents/{agent_id}/anchoring-config` endpoint
6. Add `POST /v1/agents/{agent_id}/anchor-data` endpoint (hash arbitrary JSON)
7. Fix boolean storage in `PUT /v1/agents/{agent_id}/anchoring-config`
8. Fix `client.ts` endpoint paths and payload schemas
9. Gate mock payment behind `X402_MOCK_PAYMENTS=true` env flag
10. Fix `generate-statement` to query the database

### P2 — Test reliability
11. Convert `test_agent_anchoring_smoke.py` to TestClient
12. Convert `test_x402_smoke.py` to TestClient
13. Register pytest markers in `pytest.ini`
14. Expand CI workflow

### P3 — Repo hygiene
15. Remove `.env.local`, `tsbuildinfo`, CPU profile, `test_agentic.db`
16. Update `.gitignore` to prevent recurrence
17. Fix README clone URL and duplicate content
18. Fix broken doc links (wrong relative paths)

### P4 — New docs
19. Add `docs/RELEASE_CHECKLIST.md`
20. Add `docs/KNOWN_LIMITATIONS.md`
21. Add `.claude/settings.json` with Flare AI Skills config
22. Add `docs/concepts/flare-native-implementations.md`

### P5 — SDK completeness
23. Add agent CRUD + anchoring methods to TypeScript SDK
24. Add agent methods to Python SDK

---

*This audit was generated as part of the ProofRails v2.2 release process.  
All items marked P0 and P1 must be resolved before merging to main.*
