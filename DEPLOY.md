# Deployment Guide

Complete instructions for deploying the ISO 20022 Middleware with x402 payment support. Covers the smart contract, backend API, background worker, and Next.js frontend.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Environment Variables](#environment-variables)
4. [Step 1 — Deploy the X402Facilitator Contract](#step-1--deploy-the-x402facilitator-contract)
5. [Step 2 — Database Setup](#step-2--database-setup)
6. [Step 3 — Backend (API + Worker)](#step-3--backend-api--worker)
7. [Step 4 — Frontend (web-alt)](#step-4--frontend-web-alt)
8. [Step 5 — Post-Deploy Verification](#step-5--post-deploy-verification)
9. [Railway Reference](#railway-reference)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients / Agents                      │
└────────────────┬────────────────────────┬───────────────────┘
                 │ HTTP (x402 payments)    │ Browser (UI)
                 ▼                         ▼
┌────────────────────────┐   ┌────────────────────────────────┐
│  FastAPI Backend        │   │  Next.js Frontend (web-alt)    │
│  :8000                  │◄──│  :3000                          │
│  + RQ Worker            │   │  /x402 dashboard               │
└─────────┬──────────────┘   └────────────────────────────────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
┌────────┐  ┌────────┐
│Postgres│  │ Redis  │
│  :5432 │  │  :6379 │
└────────┘  └────────┘
          │
          ▼
┌──────────────────────────────┐
│  Flare Mainnet / Coston2     │
│  X402Facilitator.sol         │  ← EIP-3009 payment settlement
│  EvidenceAnchor.sol          │  ← ISO bundle anchoring
└──────────────────────────────┘
```

**Components:**
- **FastAPI backend** — ISO 20022 processing, x402 payment verification, REST API
- **RQ worker** — background jobs (anchoring, evidence bundling)
- **PostgreSQL** — primary database
- **Redis** — job queue and idempotency cache
- **X402Facilitator contract** — on-chain settlement of EIP-3009 USDT0 payments on Flare
- **web-alt** — Next.js dashboard (receipts, agents, x402 analytics, facilitator config)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend + contract tooling |
| npm | 9+ | JS package management |
| PostgreSQL | 15+ | Production database |
| Redis | 7+ | Job queue |
| Git | any | Clone repo |

**Wallets / accounts:**
- A deployer wallet with FLR on Flare mainnet (or C2FLR on Coston2 testnet) for gas
- A recipient wallet address for collecting x402 payments (can be a multisig — recommended for mainnet)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in every value marked **required**.

### Core

```bash
APP_ENV=prod                    # dev | prod
PUBLIC_BASE_URL=https://your-api-url.com
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
ARTIFACTS_DIR=artifacts
AUTO_CREATE_DB=0                # always use Alembic in production
```

### Authentication

```bash
# Comma-separated list of allowed API keys (for machine clients)
API_KEYS=key1,key2
```

### CORS

```bash
# Comma-separated list of allowed origins for the frontend
ALLOW_ORIGINS=https://your-frontend-url.com,http://localhost:3000
```

### Anchoring (EvidenceAnchor)

```bash
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ANCHOR_CONTRACT_ADDR=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
ANCHOR_PRIVATE_KEY=0xYourAnchorWalletPrivateKey   # wallet that pays gas for anchoring
ANCHOR_ABI_PATH=contracts/EvidenceAnchor.abi.json
```

### x402 — Shared

```bash
# Fallback recipient used when path-specific recipient is not set
X402_RECIPIENT_ADDRESS=0xYourRecipientWallet

# Enable/disable individual payment paths (all default to true)
X402_ENABLE_BASE_USDC=true
X402_ENABLE_FLARE_USDT0=true
X402_ENABLE_FLARE_NATIVE_FLR=true
```

### x402 — Base USDC path

```bash
X402_BASE_RPC_URL=https://mainnet.base.org
X402_USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
X402_USDC_AMOUNT=0.001                          # price per call in USDC
X402_BASE_RECIPIENT=0xYourBaseRecipient         # override X402_RECIPIENT_ADDRESS for USDC
```

### x402 — Flare USDT0 path (EIP-3009 facilitator)

```bash
X402_FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
X402_FLARE_CHAIN_ID=14
X402_USDT0_FLARE_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D
X402_USDT0_DECIMALS=6
X402_USDT0_AMOUNT=0.001                         # price per call in USDT0
X402_FLARE_FACILITATOR_ADDRESS=0xYourFacilitatorAddress   # set after Step 1
X402_USDT0_RECIPIENT=0xYourFlareRecipient
X402_FLARE_CONFIRMATIONS=1
```

### x402 — Flare native FLR path

```bash
X402_FLR_AMOUNT=0.05
X402_FLR_RECIPIENT=0xYourFlareRecipient
```

### x402 — Settlement mode

```bash
# "client" = the paying client submits the settlement tx and provides the tx hash
# "server" = the API server submits the EIP-3009 authorization to the facilitator
X402_SETTLEMENT_MODE=client

# Only required when X402_SETTLEMENT_MODE=server
X402_SETTLER_PRIVATE_KEY=0xYourSettlerPrivateKey
```

### AI (optional)

```bash
AI_PROVIDER=openai           # openai | anthropic | none
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

---

## Step 1 — Deploy the X402Facilitator Contract

The X402Facilitator is the on-chain EIP-3009 settlement contract that receives USDT0 payments from agents. It must be deployed before the backend can accept USDT0 payments.

### 1a. Install dependencies

```bash
npm install
```

### 1b. Compile contracts

```bash
npm run compile
# or: npx hardhat compile
```

Expected output: `Compiled 6 Solidity files successfully`

### 1c. Set deployment env vars

```bash
export DEPLOYER_PRIVATE_KEY=0xYourDeployerPrivateKey
export X402_RECIPIENT_ADDRESS=0xYourRecipientOrMultisigAddress
```

> **Mainnet recommendation:** use a Gnosis Safe multisig as the owner/recipient. The owner controls `addSupportedToken`, `setMinimumAmount`, `pause`, and `unpause`.

### 1d. Deploy to testnet first (Coston2)

```bash
node scripts/deploy_x402_facilitator.js --network coston2
```

The script:
1. Deploys `X402Facilitator` with `X402_RECIPIENT_ADDRESS` as owner
2. Calls `addSupportedToken` for the USDT0 token address (if `MOCK_USDT0_COSTON2` is set)
3. Sets minimum payment to 1000 raw units (0.001 USDT0)
4. Writes deployment artifact to `deployments/coston2/x402-facilitator.json`

Get testnet FLR from the [Coston2 faucet](https://faucet.flare.network).

### 1e. Deploy to Flare mainnet

```bash
node scripts/deploy_x402_facilitator.js --network flare
```

Artifact written to `deployments/flare/x402-facilitator.json`. The `facilitator` address in that file is what you set as `X402_FLARE_FACILITATOR_ADDRESS`.

### 1f. Verify deployment

```bash
# Check contract is live and USDT0 is supported
cast call <FACILITATOR_ADDRESS> "supportedTokens(address)(bool)" \
  0xe7cd86e13AC4309349F30B3435a9d337750fC82D \
  --rpc-url https://flare-api.flare.network/ext/C/rpc
# Should return: true
```

---

## Step 2 — Database Setup

### Local / development (SQLite)

```bash
pip install -r requirements.txt
alembic upgrade head
```

SQLite database created at `dev.db`. No Postgres needed for development.

### Production (PostgreSQL)

```bash
# With DATABASE_URL set in environment:
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname alembic upgrade head
```

**Migration history** (applied in order):
1. `8d23500035d7` — initial schema
2. `5a8e64824892` — add x402_payments table
3. `ca553b86c849` — add AI config to agents
4. `d8f9c3b21456` — add agent anchoring table
5. `f3a9d1c05e82` — extend x402_payments for USDT0/Flare multi-chain (10 new columns, replay-protection indexes)

To check current migration state:
```bash
alembic current
```

---

## Step 3 — Backend (API + Worker)

### Option A: Docker Compose (recommended for staging / self-hosted)

```bash
# 1. Copy and fill in environment
cp .env.example .env
# Edit .env — set DATABASE_URL, Redis, x402 vars, etc.

# 2. Start all services
docker-compose up -d

# 3. Run migrations (first boot only)
docker-compose exec api alembic upgrade head

# 4. Check health
curl http://localhost:8000/health
```

Services started:
- `api` — FastAPI on port 8000
- `worker` — RQ background worker
- `postgres` — PostgreSQL on port 5432
- `redis` — Redis on port 6379

### Option B: Railway (recommended for production)

See [Railway Reference](#railway-reference) below.

### Option C: Manual (development)

```bash
pip install -r requirements.txt
alembic upgrade head

# Terminal 1: API
uvicorn app.main:app --reload --port 8000

# Terminal 2: Worker
python worker.py
```

---

## Step 4 — Frontend (web-alt)

The `web-alt` directory is a standalone Next.js 14 application. It proxies all `/api/...` requests to the backend.

### 4a. Install dependencies

```bash
cd web-alt
npm install
```

### 4b. Configure environment

```bash
cp .env.production.example .env.production.local
```

Required variables:

```bash
NEXT_PUBLIC_API_URL=https://your-api-url.com   # no trailing slash
```

### 4c. Build and start

```bash
npm run build
npm start           # runs on port 3000
```

Or for development:
```bash
npm run dev
```

### 4d. Deploy to Railway

The `web-alt/railway.json` is pre-configured. Push to Railway and set:

```bash
NEXT_PUBLIC_API_URL=https://your-railway-api-url.up.railway.app
```

### x402 Dashboard

Once deployed, the x402 dashboard is at `/x402`. It shows:

| Tab | Contents |
|-----|---------|
| Payment History | Filterable table of all verified payments (currency, chain, status, payer) |
| Revenue | Revenue summary cards, bar chart by payment type, per-endpoint breakdown, CSV export |
| Configuration | Live facilitator config pulled from `/v1/x402/facilitator-config` |
| Checkout Demo | Interactive `PaymentModal` for testing end-user USDT0/USDC/FLR payment flows |

---

## Step 5 — Post-Deploy Verification

### 5a. Backend health

```bash
curl https://your-api-url.com/health
# {"status": "ok"}
```

### 5b. x402 pricing endpoint

```bash
curl https://your-api-url.com/v1/x402/pricing
```

Should return the list of protected endpoints with prices.

### 5c. Test the payment gate

```bash
# Should return 402 Payment Required
curl -X POST https://your-api-url.com/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR"}'
```

Expected response:
```json
{
  "version": "1.0",
  "error": "payment_required",
  "accepts": [...]
}
```

### 5d. Test USDC payment (Base)

1. Send 0.001 USDC to `X402_BASE_RECIPIENT` on Base mainnet
2. Re-send the request with `X-PAYMENT` header:

```bash
curl -X POST https://your-api-url.com/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"chain":"base","chain_id":8453,"currency":"USDC","payment_type":"erc20_transfer","tx_hash":"0xYourTxHash","amount":"0.001","recipient":"0xYourRecipient"}' \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR"}'
```

### 5e. Test USDT0 payment (Flare, client-settled)

1. Sign a `transferWithAuthorization` for 1000 raw USDT0 (0.001 USDT0, 6 decimals) using EIP-3009
2. Submit the signed authorization to `X402Facilitator.settlePayment(payload)` on Flare
3. Pass the resulting tx hash as `settlement_tx_hash` in the X-PAYMENT header

### 5f. Dashboard

Open `https://your-frontend-url.com/x402` and confirm payment records appear.

---

## Railway Reference

### Backend service (API)

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Railway Postgres connection string |
| `REDIS_URL` | Railway Redis connection string |
| `APP_ENV` | `prod` |
| `PUBLIC_BASE_URL` | `https://your-api.up.railway.app` |
| `ALLOW_ORIGINS` | `https://your-frontend.up.railway.app` |
| `AUTO_CREATE_DB` | `0` |
| `X402_FLARE_FACILITATOR_ADDRESS` | address from Step 1 |
| `X402_USDT0_RECIPIENT` | your recipient wallet |
| `X402_FLR_RECIPIENT` | your recipient wallet |
| `X402_BASE_RECIPIENT` | your recipient wallet |
| `X402_RECIPIENT_ADDRESS` | fallback recipient |
| `ANCHOR_PRIVATE_KEY` | anchoring wallet key |

**Start command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Post-deploy command (run once):**
```
alembic upgrade head
```

### Worker service

Same environment variables as the API service except:
- No `PORT` binding needed
- Start command: `python worker.py`

### Frontend service (web-alt)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-api.up.railway.app` |

**Build command:** `npm run build`  
**Start command:** `npm start`

---

## Troubleshooting

### `X402_FLARE_FACILITATOR_ADDRESS not set` error

The Flare USDT0 payment path is enabled but the facilitator contract hasn't been deployed yet, or the env var hasn't been set. Complete Step 1 and set the env var.

### 402 returned instead of 200 after sending payment

Common causes:
- Wrong recipient in the X-PAYMENT header (must match `X402_*_RECIPIENT` env var)
- TX not yet confirmed (wait for 1 block on Flare)
- `tx_hash` already used in a previous request (replay protection)
- `eip3009_nonce` already used (nonce replay protection — generate a fresh nonce per payment)

### `TokenNotSupported` revert from facilitator contract

The token address isn't in the facilitator's allowlist. Call `addSupportedToken(tokenAddress)` from the owner wallet.

### Migrations fail with `relation already exists`

The database already has some tables from `AUTO_CREATE_DB=1`. Run:
```bash
alembic stamp head
```
to mark the DB as current without re-running migrations.

### `pytest_ethereum` plugin crash during tests

The `pytest.ini` already includes `-p no:pytest_ethereum`. If running tests in a new environment:
```bash
pip install pytest pytest-asyncio
python -m pytest
```

### Frontend shows `CORS error`

Add your frontend URL to `ALLOW_ORIGINS` in the backend environment.

---

## Security Checklist Before Mainnet

- [ ] X402Facilitator owner is a Gnosis Safe multisig, not an EOA
- [ ] `ANCHOR_PRIVATE_KEY` and `X402_SETTLER_PRIVATE_KEY` stored in Railway secrets, not `.env` files
- [ ] External smart contract audit completed (see `docs/security/X402Facilitator-audit.md`)
- [ ] `X402_ENABLE_FLARE_USDT0=true` only after facilitator is deployed and verified on testnet
- [ ] `X402_SETTLEMENT_MODE=server` only if you control a secure server-side wallet
- [ ] PostgreSQL not exposed publicly (Railway/Docker internal networking only)
- [ ] `APP_ENV=prod` to enable stricter validation
