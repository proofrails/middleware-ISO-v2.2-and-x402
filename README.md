# ProofRails

**ProofRails** is an open translation and evidence layer for on-chain payments. It turns blockchain transactions and agent-triggered payments into ISO 20022-style records, packages them into audit-grade evidence bundles, and anchors their hashes on-chain for independent verification.

This branch (`agentic`) extends ProofRails v2.2 with:

- **x402 payment-gated API endpoints** — premium API access paid with USDC micropayments on Base
- **AI/XMTP agent workflows** — autonomous agents that pay for, generate, and verify payment evidence
- **Agent-triggered anchoring** — agents can hash and anchor arbitrary data to Flare on-chain
- **Flare-native paths** — Flare EVM anchoring (implemented), FTSO FX rates (implemented), FDC/FAssets/Smart Accounts (proposed)

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Clients                                                         │
│   Web UI (Next.js) │ Python SDK │ TS SDK │ XMTP Agent           │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ HTTP REST + X-API-Key
┌──────────────────────────────────▼───────────────────────────────┐
│  ProofRails API (FastAPI)                                        │
│   Receipts / ISO XML / Statements / Verification                 │
│   x402 Payment Gate / Premium Endpoints                          │
│   Agents / Anchoring / x402 Analytics                            │
│   Projects / Auth / Webhooks                                     │
└─────────────────┬────────────────────────┬───────────────────────┘
                  │                        │
         ┌────────▼────────┐    ┌─────────▼─────────┐
         │  Flare C-Chain  │    │  Base (USDC)       │
         │  Anchor contract│    │  x402 payment      │
         │  FTSO v2 feeds  │    │  verification      │
         └─────────────────┘    └───────────────────┘
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
| x402 production payment (real USDC) | Implemented (requires live Base RPC) |
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
