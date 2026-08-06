# ProofRails

**ProofRails** is an open translation and evidence layer for on-chain payments. It turns blockchain transactions and agent-triggered payments into ISO 20022-style records, packages them into audit-grade evidence bundles, and anchors their hashes on-chain for independent verification.

This branch (`agentic`) extends ProofRails v2.2 with:

- **x402 payment-gated API endpoints** — premium API access paid with USDC on Base or FLR on Flare
- **AI/XMTP agent workflows** — autonomous agents that pay for, generate, and verify payment evidence
- **Agent-triggered anchoring** — agents can hash and anchor arbitrary data to Flare on-chain
- **Flare-native paths** — Flare EVM anchoring (implemented), FTSO FX rates (implemented), FDC/FAssets/Smart Accounts (proposed)

## Architecture

ProofRails is an open middleware layer that turns blockchain payment transactions into ISO 20022-compliant records, packages them into cryptographic evidence bundles, and anchors their hashes on-chain for independent verification.

## What it does

- **ISO 20022 message generation** — converts on-chain payments into pain.001, pacs.008, camt.053/054, pacs.004, and more (15 message types)
- **Evidence bundles** — deterministic ZIP packages with a canonical hash for each payment record
- **On-chain anchoring** — bundle hashes anchored to Flare C-Chain (or any EVM chain in tenant mode)
- **Bundle verification** — trustless verification of any evidence bundle against the on-chain anchor
- **x402 payment gating** — pay-per-use premium API access with USDC on Base or FLR on Flare
- **Multi-tenant projects** — isolated projects with Sign-In With Ethereum (SIWE) auth and per-project API keys
- **Statements** — camt.052 (intraday) and camt.053 (daily) account statement generation
- **Refunds** — pacs.004 return message generation

API docs auto-generated at `http://localhost:8000/docs`.

## Quickstart

```bash
git clone https://github.com/proofrails/middleware-ISO-v2.2-and-x402.git
cd middleware-ISO-v2.2-and-x402

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — see Environment variables below
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (optional)
cd web-alt && npm install && npm run dev
```

Open `http://localhost:3000` for the dashboard, `http://localhost:8000/docs` for the API.

## Environment variables

```env
# Database
DATABASE_URL=sqlite:///./local.db
AUTO_CREATE_DB=true

# Flare anchoring
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ANCHOR_CONTRACT_ADDR=0x...
ANCHOR_PRIVATE_KEY=0x...

# x402 payment gating
X402_RECIPIENT=0x...           # USDC recipient on Base
X402_FLR_RECIPIENT=0x...       # FLR recipient on Flare (defaults to X402_RECIPIENT)
X402_MOCK_PAYMENTS=true        # DEV ONLY — skip on-chain verification

# Optional
RATE_LIMIT_ENABLED=false
FTSO_ENABLED=false
```

See `.env.example` for the full list.

## Create a receipt

```bash
# Create a project and get an API key from the UI, then:
curl -X POST http://localhost:8000/v1/receipts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tip_tx_hash": "0xabc...",
    "chain": "flare",
    "amount": "100.00",
    "currency": "USD",
    "sender_wallet": "0xsender...",
    "receiver_wallet": "0xreceiver...",
    "reference": "INV-2026-001"
  }'
```

The receipt is processed, ISO XML is generated, an evidence bundle is built, and the bundle hash is anchored on Flare. The response includes a `bundle_url` and `flare_txid` for verification.

## Verify a bundle

```bash
curl -X POST http://localhost:8000/v1/iso/verify \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bundle_hash": "0x..."}'
```

## x402 premium endpoints

Premium endpoints return `HTTP 402` until a micropayment is made. The 402 body lists accepted options (USDC on Base or FLR on Flare). Send the transfer, then retry with the tx hash in the `X-PAYMENT` header.

```bash
# Step 1 — get the payment requirements
curl -X POST http://localhost:8000/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -d '{"bundle_hash": "0x..."}'
# → 402 with accepted: [{currency: USDC, chain: base}, {currency: FLR, chain: flare}]

# Step 2 — retry after paying
curl -X POST http://localhost:8000/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xabc...","amount":"0.001","currency":"USDC","chain":"base","recipient":"0x..."}' \
  -d '{"bundle_hash": "0x..."}'
```

| Endpoint | USDC | FLR |
|----------|------|-----|
| `POST /v1/x402/premium/verify-bundle` | 0.001 | 0.05 |
| `POST /v1/x402/premium/generate-statement` | 0.005 | 0.25 |
| `POST /v1/x402/premium/fx-lookup` | 0.0005 | 0.05 |
| `POST /v1/x402/premium/bulk-verify` | 0.01 | 0.50 |
| `POST /v1/x402/premium/refund` | 0.001 | 0.15 |

For development, set `X402_MOCK_PAYMENTS=true` to skip on-chain verification.

## SDKs

**TypeScript:**
```ts
import IsoMiddlewareClient from "iso-middleware-sdk";
const api = new IsoMiddlewareClient({ baseUrl: "http://localhost:8000", apiKey: "..." });
const page = await api.listReceipts({ scope: "mine", page: 1, page_size: 20 });
```
┌──────────────────────────────────────────────────────────────────┐
│  Clients                                                         │
│   Web UI (Next.js) │ Python SDK │ TS SDK │ XMTP Agent           │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP REST + X-API-Key
┌──────────────────────────────▼───────────────────────────────────┐
│  ProofRails API (FastAPI)                                        │
│   Receipts / ISO XML / Statements / Verification                 │
│   x402 Payment Gate / Premium Endpoints                          │
│   Agents / Anchoring / x402 Analytics                            │
│   Projects / Auth / Webhooks                                     │
└─────────────────┬────────────────────────┬───────────────────────┘
                  │                        │
         ┌────────▼────────┐    ┌─────────▼─────────┐
         │  Flare C-Chain  │    │ Base & Flare(USDC)│
         │  Anchor contract│    │  x402 payment     │
         │  FTSO v2 feeds  │    │  verification     │
         └─────────────────┘    └───────────────────┘
                                   x402: USDC (Base) or FLR (Flare)
```

## Release status

**Branch: agentic — v2.2 pre-release**

| Feature | Status |
|---------|--------|
| Receipt creation (Flare) | Implemented |
| ISO 20022 message generation (pain.001, pacs.008, camt.053/054, pacs.004) | Implemented |
| pain.008 direct debit | Implemented |
| Evidence bundle + hash | Implemented |
| On-chain anchoring (Flare EVM) | Implemented |
| Bundle verification | Implemented |
| Project / API key management | Implemented |
| Refunds (pacs.004) | Implemented |
| x402 payment gating | Implemented |
| x402 mock mode (dev only) | Implemented |
| FTSO v2 FX rates | Implemented |
| Agent CRUD | Implemented |
| Agent AI config (simple/shared/custom) | Implemented |
| Agent anchoring (anchor-data, config) | Implemented |
| XMTP agent — list/get/verify/statement/refund | Implemented |
| XMTP agent — status/anchor/list anchors/verify anchor | Implemented |
| Web UI — agent management, anchoring | Implemented |
| TypeScript SDK — full surface | Implemented |
| Python SDK — full surface | Implemented |
| Webhook subscriptions | Implemented |
| Proactive wallet monitoring | Implemented |
| x402 production payment (USDC on Base) | Implemented (requires live Base RPC) |
| x402 production payment (FLR on Flare) | Implemented (requires live Flare RPC) |
| FDC-backed receipt verification | Proposed |
| FAssets ISO flows | Proposed |
| XRPL Smart Accounts integration | Proposed |
| Private key encryption (agent anchoring) | Known gap — see KNOWN_LIMITATIONS.md |

This branch is **not production-ready** until the [release checklist](docs/RELEASE_CHECKLIST.md) passes manual verification.

## Quickstart (local)

```bash
git clone https://github.com/proofrails/middleware-ISO-v2.2-and-x402.git
cd middleware-ISO-v2.2-and-x402

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set AUTO_CREATE_DB=true, X402_MOCK_PAYMENTS=true for local dev
uvicorn app.main:app --reload --port 8000

# Run tests (in-process, no live services needed)
pytest tests/ -q
# Expected: 100+ passed

# Frontend (optional)
cd web-alt && npm install && npm run dev
```

API docs: `http://localhost:8000/docs`

## Environment variables

See `.env.example` for the full list. Key variables:

```env
DATABASE_URL=sqlite:///./local.db
AUTO_CREATE_DB=true
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ANCHOR_CONTRACT=0x...
ANCHOR_PRIVATE_KEY=0x...
X402_MOCK_PAYMENTS=true        # DEV ONLY — never in production
RATE_LIMIT_ENABLED=false       # disable for local dev
```

## Project structure

```
app/                    FastAPI backend
  api/routes/           Route handlers
  models.py             SQLAlchemy models
  schemas.py            Pydantic schemas
  anchor.py             Flare anchor module
  flare/ftso.py         FTSO v2 integration
  x402.py               x402 payment verification
alembic/                Database migrations
agents/iso-x402-agent/  XMTP agent (TypeScript)
packages/sdk/           TypeScript SDK
packages/sdk-python/    Python SDK
web-alt/                Next.js frontend
docs/                   Full documentation
tests/                  pytest test suite
```

## Documentation

Full docs are in [docs/INDEX.md](docs/INDEX.md).

Quick links:
- [Quickstart](docs/guides/quickstart-local.md)
- [Create First Receipt](docs/guides/create-first-receipt.md)
- [x402 Paid Endpoints](docs/guides/use-x402-paid-endpoints.md)
- [Configure Agent Anchoring](docs/guides/configure-agent-anchoring.md)
- [Deploy XMTP Agent](docs/guides/deploy-xmtp-agent.md)
- [Flare AI Skills](docs/guides/use-flare-ai-skills.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)

## Tests

```bash
# Python backend
pytest tests/ -q

# TypeScript SDK build
cd packages/sdk && npm install && npm run build

# XMTP agent typecheck
cd agents/iso-x402-agent && npm install && npx tsc --noEmit

# Next.js frontend build
cd web-alt && npm install && npm run build
```

## x402 payment recipient

The default x402 recipient for premium endpoints is configured in `.env` via `X402_RECIPIENT`. For testing, set any EVM address.

## Contributing

See [docs/RELEASE_AUDIT.md](docs/RELEASE_AUDIT.md) for the full list of known issues and planned work. Open an issue at [github.com/proofrails/middleware-ISO-v2.2-and-x402/issues](https://github.com/proofrails/middleware-ISO-v2.2-and-x402/issues).

## License

MIT
**Python:**
```python
from iso_middleware_sdk import ISOClient
client = ISOClient(base_url="http://localhost:8000", api_key="...")
page = client.list_receipts(scope="mine", page=1, page_size=20)
```

## Project structure

```
app/                    FastAPI backend
  api/routes/           Route handlers
  models.py             SQLAlchemy models
  anchor.py             Flare anchor module
  flare/ftso.py         FTSO v2 FX rates
  x402.py               x402 payment verification
alembic/                Database migrations
packages/sdk/           TypeScript SDK
packages/sdk-python/    Python SDK
web-alt/                Next.js frontend
tests/                  pytest test suite
```

## Tests

```bash
# Python backend
pytest tests/ -q

# TypeScript SDK build
cd packages/sdk && npm install && npm run build

# Frontend build
cd web-alt && npm install && npm run build
```

## Agents

An XMTP messaging agent is available in `agents/iso-x402-agent/` — it lets users interact with the API via natural language over XMTP messaging, with automatic x402 micropayment handling. See its [README](agents/iso-x402-agent/README.md).

For the full agentic branch with AI-driven workflows, Flare-native features, and advanced agent anchoring, see the [`agentic` branch](https://github.com/proofrails/middleware-ISO-v2.2-and-x402/tree/agentic).

## License

MIT

::::

note: add AI native docs
