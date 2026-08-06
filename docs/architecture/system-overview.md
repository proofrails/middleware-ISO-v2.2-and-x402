# Architecture: System Overview

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients                                                        │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Web UI   │  │ Python SDK   │  │ XMTP Agent             │   │
│  │ (Next.js)│  │ / TS SDK     │  │ (iso-x402-agent)       │   │
│  └────┬─────┘  └──────┬───────┘  └───────────┬────────────┘   │
│       │               │                       │                 │
│       └───────────────┴───────────────────────┘                 │
│                       │ HTTP / REST                             │
└───────────────────────┼─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│  ProofRails API (FastAPI)                                       │
│                                                                 │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Receipts  │  │ x402 Premium │  │ Agents / Anchoring      │ │
│  │ ISO XML   │  │ Payment Gate │  │ Config / anchor-data    │ │
│  │ Verify    │  │ Analytics    │  │ Activity Feed           │ │
│  └─────┬─────┘  └──────┬───────┘  └───────────┬─────────────┘ │
│        │               │                       │               │
│  ┌─────▼───────────────▼───────────────────────▼─────────────┐ │
│  │  SQLAlchemy ORM (PostgreSQL / SQLite)                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Background tasks: anchor submissions, monitoring, webhooks    │
└─────────────────┬───────────────────────────┬───────────────────┘
                  │                           │
          ┌───────▼───────┐         ┌────────▼────────┐
          │  Flare C-Chain│         │  Base (USDC)    │
          │  Anchor       │         │  x402 payment   │
          │  contract     │         │  verification   │
          └───────────────┘         └─────────────────┘
```

## Data flow

1. **Receipt creation**: Client POSTs a receipt → API validates → ISO XML generated → bundle assembled → hash computed → background task submits hash to Flare anchor contract.

2. **x402 payment**: Agent calls premium endpoint → 402 returned with pricing → agent sends USDC on Base → retries with `X-PAYMENT` header → backend verifies USDC transfer on Base → payment recorded → response returned.

3. **Agent anchoring**: Agent calls `POST /anchor-data` → backend hashes JSON → records `AgentAnchor` → if `submit_onchain=true`, background task calls anchor contract.

4. **Verification**: Any party calls `POST /verify` with hash → backend queries anchor contract → returns confirmation with block timestamp.

## Tech stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL (production), SQLite (dev/test) |
| Migrations | Alembic |
| Frontend | Next.js 14 (App Router) |
| Agent | TypeScript / Node.js / XMTP JS SDK |
| Chain (anchoring) | Flare C-Chain via JSON-RPC |
| Chain (payments) | Base via JSON-RPC + ethers v6 |
| Containerisation | Docker + docker-compose |
| CI | GitHub Actions |

## See also

- [Receipt Lifecycle](./receipt-lifecycle.md)
- [Agentic Payment Flow](./agentic-payment-flow.md)
- [Security Model](./security-model.md)
