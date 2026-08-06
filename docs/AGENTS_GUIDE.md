# XMTP Agents Guide

This guide covers the autonomous XMTP agent system — architecture, deployment, command handling, AI modes, and the x402 payment integration.

---

## Overview

The ISO Middleware agent is a TypeScript service that listens for messages via the [XMTP](https://xmtp.org/) decentralized messaging protocol. Users send natural language or structured commands to the agent's XMTP address, and the agent processes them — listing receipts, verifying bundles, generating statements, initiating refunds — paying for premium operations automatically via x402 micropayments.

```
User (Converse app / XMTP client)
      │
      │  XMTP message: "verify https://ipfs.io/ipfs/Qm..."
      ▼
┌──────────────────────────┐
│  XMTP Agent              │
│  - Receives message      │
│  - Parses command (AI    │
│    or simple matching)   │
│  - Calls middleware API  │
│  - Pays USDC if needed   │
│  - Sends reply via XMTP  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  ISO Middleware API       │
│  /v1/receipts            │
│  /v1/x402/premium/...    │
│  /v1/iso/verify          │
└──────────────────────────┘
```

---

## Architecture

### Source Structure

```
agents/iso-x402-agent/
├── src/
│   ├── index.ts              # Entry point — loads config, starts agent
│   ├── agent.ts              # ISOAgent class — XMTP client, message routing
│   ├── handlers/
│   │   ├── receipts.ts       # list / get receipt handlers
│   │   ├── verify.ts         # Bundle verification (paid via x402)
│   │   ├── statements.ts     # Statement generation (paid via x402)
│   │   ├── refunds.ts        # Refund initiation (paid via x402)
│   │   └── help.ts           # Help text
│   ├── utils/
│   │   ├── parser.ts         # Command parsing (simple + AI modes)
│   │   └── logger.ts         # Structured logging
│   └── x402/
│       └── client.ts         # ISOMiddlewareClient with x402 payment logic
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── railway.json              # Railway deployment config
├── app.json                  # Heroku deployment config
├── package.json
└── tsconfig.json
```

### Key Classes

**`ISOAgent`** (`src/agent.ts`): Core agent class. Initializes the XMTP client with the agent's wallet, streams all incoming messages, parses commands via `parseCommandWithAI()`, routes to the appropriate handler, and sends replies.

**`ISOMiddlewareClient`** (`src/x402/client.ts`): HTTP client for the middleware API. Free endpoints (`listReceipts`, `getReceipt`) use standard requests. Premium endpoints (`verifyBundle`, `generateStatement`, `initiateRefund`) use `makePaidRequest()` which transfers USDC before making the API call with the `X-PAYMENT` header.

---

## Commands

### Free Commands

| Command | Example | Description |
|---------|---------|-------------|
| `help` | `help` | Show available commands |
| `list [limit]` | `list 5` | List recent receipts |
| `get <receipt_id>` | `get 550e8400-...` | Get receipt details |

### Paid Commands (x402)

| Command | Example | Price | Description |
|---------|---------|-------|-------------|
| `verify <url>` | `verify https://ipfs.io/ipfs/Qm...` | 0.001 USDC | Verify evidence bundle |
| `statement <date>` | `statement 2026-01-20` | 0.005 USDC | Generate daily statement |
| `refund <receipt_id>` | `refund 550e8400-...` | 0.003 USDC | Initiate payment refund |

Payments are automatic — the agent transfers USDC from its wallet to the configured recipient before making the API call. No user interaction is needed beyond sending the command.

---

## AI Modes

The agent supports three modes for parsing incoming messages. Configure via `AI_MODE` environment variable or the UI at `/agents → AI Settings`.

### Simple Mode (Default)

Exact prefix matching. Fast, free, no API calls. Commands must follow a strict format:

```
list 5            → { action: "list", args: { limit: 5 } }
get abc123        → { action: "get", args: { receiptId: "abc123" } }
verify https://.. → { action: "verify", args: { bundleUrl: "https://..." } }
help              → { action: "help", args: {} }
```

### Shared AI Mode

Uses the middleware's system AI (OpenAI) via `POST /v1/ai/parse-command`. Free for agents — the middleware operator pays the AI costs. Supports natural language:

```
"Can you show me my recent receipts?"
"Is this bundle valid? https://ipfs.io/ipfs/Qm..."
"Refund receipt abc123, it was a duplicate"
```

Custom system prompts are supported — set `AI_SYSTEM_PROMPT` or configure via `PUT /v1/agents/{id}/ai-config`.

### Custom AI Mode

The agent uses your own AI provider and API key. You control the model, billing, and prompting.

```bash
AI_MODE=custom
AI_PROVIDER=openai       # or anthropic, google, custom
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

---

## Setup & Deployment

### Prerequisites

- Node.js 18+
- An Ethereum wallet (private key) for the agent
- The ISO Middleware API running and accessible
- (Optional) USDC on Base chain for paid commands

### Local Development

```bash
cd agents/iso-x402-agent

# Install dependencies
npm install

# Configure
cp .env.example .env
# Edit .env with your settings

# Build and run
npm run build
npm start

# Or run in dev mode (ts-node)
npm run dev
```

### Environment Variables

```bash
# Required
WALLET_PRIVATE_KEY=0x...              # Agent's wallet (signs XMTP + payments)
ISO_MW_API_URL=http://localhost:8000  # Middleware API URL

# Optional - API Auth
ISO_MW_API_KEY=your_api_key           # API key for authenticated endpoints

# Optional - XMTP
XMTP_ENV=dev                          # "dev" for testing, "production" for mainnet

# Optional - x402 Payments
X402_RECIPIENT=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8  # Payment recipient
CHAIN_RPC_URL=https://mainnet.base.org                       # Base chain RPC
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913    # USDC on Base

# Optional - AI
AI_MODE=simple                        # simple | shared | custom
AI_SYSTEM_PROMPT=...                  # Custom system prompt
AI_PROVIDER=openai                    # For custom mode
AI_API_KEY=sk-...                     # For custom mode
AI_MODEL=gpt-4o-mini                  # For custom mode

# Optional - Agent Anchoring
ANCHOR_ENABLED=true                   # Enable anchoring feature
ANCHOR_ON_PAYMENT=true                # Auto-anchor on x402 payments
ANCHOR_WALLET=0x...                   # Dedicated wallet for gas fees

# Optional - Meta
AGENT_NAME=ISO Anchoring Agent
LOG_LEVEL=info                        # debug, info, warn, error
```

### Docker

```bash
# Using docker-compose
docker-compose up -d

# Or build manually
docker build -t iso-agent .
docker run -d --env-file .env --name iso-agent --restart unless-stopped iso-agent
```

### PM2 (Production VPS)

```bash
npm install -g pm2
npm run build
pm2 start dist/index.js --name iso-agent
pm2 save
pm2 startup  # Auto-restart on reboot
```

### Railway

The repo includes `railway.json` for one-click deployment:

```bash
railway login
railway init
railway up
```

### Heroku

The repo includes `app.json`:

```bash
heroku create iso-agent
heroku config:set WALLET_PRIVATE_KEY=0x...
heroku config:set ISO_MW_API_URL=https://your-api.com
git push heroku main
```

---

## Agent Management API

The middleware provides a full REST API for managing agents programmatically.

### CRUD

```bash
# Create
curl -X POST http://localhost:8000/v1/agents \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent", "wallet_address": "0x..."}'

# List
curl http://localhost:8000/v1/agents -H "X-API-Key: your-key"

# Get
curl http://localhost:8000/v1/agents/{id} -H "X-API-Key: your-key"

# Update
curl -X PUT http://localhost:8000/v1/agents/{id} \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name", "status": "paused"}'

# Delete
curl -X DELETE http://localhost:8000/v1/agents/{id} -H "X-API-Key: your-key"
```

### AI Configuration

```bash
curl -X PUT http://localhost:8000/v1/agents/{id}/ai-config \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ai_mode": "shared",
    "ai_system_prompt": "You are a payment processing assistant..."
  }'
```

### Anchoring Configuration

```bash
curl -X PUT http://localhost:8000/v1/agents/{id}/anchoring-config \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_anchor_enabled": true,
    "anchor_on_payment": true,
    "anchor_wallet": "0xDedicated..."
  }'
```

### Statistics

```bash
curl "http://localhost:8000/v1/agents/{id}/stats?days=7" -H "X-API-Key: your-key"
```

---

## Web UI Management

The dashboard at `http://localhost:3000/agents` provides a visual interface for all agent operations:

1. **Agent List** (left panel): Create, select, and view agents.
2. **Details** tab: Name, wallet, XMTP address, status.
3. **AI Settings** tab: Configure AI mode, system prompts, custom provider.
4. **Activity** tab: Recent messages and commands.
5. **Analytics** tab: Payment volume, command frequency.
6. **Anchoring** tab: Auto-anchor configuration, manual anchoring, anchor history.
7. **Pricing** tab: Per-endpoint pricing overrides.
8. **Revenue** tab: Payment tracking and revenue analytics.

---

## Adding Custom Commands

### 1. Add Parser Rule

In `src/utils/parser.ts`, add a case for the new command:

```typescript
if (trimmed.startsWith('mycommand ')) {
  const arg = trimmed.substring('mycommand '.length).trim();
  return { action: 'mycommand', args: { value: arg } };
}
```

### 2. Create Handler

Create `src/handlers/mycommand.ts`:

```typescript
import { ISOMiddlewareClient } from '../x402/client';

export async function handleMyCommand(
  client: ISOMiddlewareClient,
  args: { value: string }
): Promise<string> {
  // Call middleware API, format response
  return `Result for: ${args.value}`;
}
```

### 3. Register in Agent

In `src/agent.ts`, add the case to `handleMessage()`:

```typescript
case 'mycommand':
  response = await handleMyCommand(this.isoClient, command.args);
  break;
```

---

## Monitoring

### Logs

```bash
# PM2
pm2 logs iso-agent

# Docker
docker logs -f iso-agent

# Verbose
LOG_LEVEL=debug npm start
```

### Health Check

The agent outputs structured logs at startup:

```
🤖 ISO Middleware XMTP Agent Starting...
✅ Environment: production
✅ XMTP client initialized
✅ Connected to ISO Middleware at http://localhost:8000
✅ Agent anchoring: ENABLED
✅ Auto-anchor on payment: ENABLED
✅ Listening for messages on XMTP...
```

---

## Troubleshooting

### Agent not receiving messages

- Verify the sender and agent are on the same XMTP network (`dev` or `production`).
- Ensure the agent's wallet has been initialized on XMTP (visit [Converse](https://converse.xyz) to create an identity if needed).
- Check `XMTP_ENV` matches between sender and agent.
- Look for errors in agent logs: `LOG_LEVEL=debug npm start`.

### Payment failures

- Verify the agent's wallet has USDC on Base chain.
- Check the recipient address: `echo $X402_RECIPIENT`.
- Verify the Base RPC is accessible: `curl -X POST https://mainnet.base.org -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'`.

### AI parsing not working

- For shared mode: verify the middleware has `AI_PROVIDER` and `OPENAI_API_KEY` configured. Check with `GET /v1/ai/status`.
- For custom mode: verify `AI_API_KEY` is set and the provider is reachable.
- Try simple mode as a fallback: `AI_MODE=simple`.

### Connection to middleware fails

- Verify `ISO_MW_API_URL` is correct and the middleware is running: `curl http://localhost:8000/v1/ping`.
- If using an API key, verify it's valid: `curl -H "X-API-Key: your-key" http://localhost:8000/v1/auth/me`.

---

## Flare-Native Features

### FTSO Rates in ISO Messages

When the XMTP agent submits a receipt for a transaction on the Flare network, the middleware automatically enriches the generated `pain.001` XML with a live exchange rate from Flare's FTSO v2 oracle — no extra configuration is required.

What the agent receives back:
- `fx.json` artifact in the evidence bundle contains `"on_chain": true` and the raw FTSO value/decimals.
- `pain001.xml` carries `<RateSrc>ftso_v2</RateSrc>` and `<Desc>FLR/USD</Desc>` in `<XchgRateInf>`.

The agent can expose this to users:

```
User: "get abc123"
Agent: "Receipt abc123 — 150 FLR = $3.22 USD (rate: 0.02150, source: ftso_v2, on-chain ✓)"
```

**FTSO feed commands** (add to your agent's command handler):

```
ftso FLR/USD        → live rate for FLR/USD
ftso BTC/USD        → live rate for BTC/USD
ftso                → all feeds (cached, no payment required)
```

Map this to `GET /v1/monitor/ftso` — free, no x402 payment needed for cached rates.  For a fresh on-chain read use the paid `fx-lookup` endpoint with `provider=ftso`.

### Paying with FLR

Agents that operate on Flare can now pay for premium endpoints in native FLR instead of USDC on Base, eliminating the need to hold USDC or bridge assets.

**Update your XMTP agent config:**

```bash
# In agents/iso-x402-agent/.env
PAYMENT_CURRENCY=FLR                                              # or USDC
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
X402_RECIPIENT=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
```

**Update `src/x402/client.ts`** to send FLR instead of USDC when `PAYMENT_CURRENCY=FLR`:

```typescript
// In makePaidRequest(), select payment method based on config
const useFLR = process.env.PAYMENT_CURRENCY === 'FLR';

if (useFLR) {
  // Parse FLR option from 402 response.accepted[]
  const flrOption = response.data.accepted?.find(
    (o: any) => o.currency === 'FLR' && o.chain === 'flare'
  );
  if (!flrOption) throw new Error('FLR payment not accepted for this endpoint');

  const txHash = await sendFLR(
    flrOption.recipient,
    flrOption.amount,
    process.env.FLARE_RPC_URL!
  );
  paymentHeader = JSON.stringify({
    tx_hash: txHash,
    amount: flrOption.amount,
    recipient: flrOption.recipient,
    currency: 'FLR',
    chain: 'flare',
  });
} else {
  // Existing USDC path
  const txHash = await sendUSDC(/* ... */);
  paymentHeader = /* ... */;
}
```

**Helper: send native FLR** (add to `src/x402/client.ts`):

```typescript
import { ethers } from 'ethers';

async function sendFLR(
  recipient: string,
  amountFLR: string,
  rpcUrl: string,
): Promise<string> {
  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(process.env.WALLET_PRIVATE_KEY!, provider);
  const tx = await wallet.sendTransaction({
    to: recipient,
    value: ethers.parseEther(amountFLR),
  });
  await tx.wait();
  return tx.hash;
}
```

### Proactive Monitoring for Agent Wallets

Instead of waiting for users to submit transactions, register the agent's wallet and let the middleware watch for incoming transfers automatically:

```bash
curl -X POST http://localhost:8000/v1/monitor/wallets \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x<agent-wallet>",
    "label": "XMTP agent receipts"
  }'
```

Every transfer to the agent's wallet will automatically:
1. Create an ISO receipt.
2. Fetch the FTSO rate and embed it.
3. Bundle the evidence.
4. Anchor it on Flare.
5. Be queryable via `list` / `get` from XMTP.

**Check the monitor is running:**

```bash
curl http://localhost:8000/v1/monitor/status -H "X-API-Key: your-key"
```

**View current FTSO rates from agent (no payment needed):**

```bash
curl http://localhost:8000/v1/monitor/ftso
```

---

## Payment Pricing Reference (USDC vs FLR)

| Command | Endpoint | USDC | FLR* |
|---------|----------|------|------|
| `verify <url>` | `premium/verify-bundle` | 0.001 | 0.05 |
| `statement <date>` | `premium/generate-statement` | 0.005 | 0.25 |
| `get-iso <id>` | `premium/iso-message` | 0.002 | 0.10 |
| `fx-lookup` | `premium/fx-lookup` | 0.001 | 0.05 |
| `bulk-verify` | `premium/bulk-verify` | 0.010 | 0.50 |
| `refund <id>` | `premium/refund` | 0.003 | 0.15 |

*FLR amounts are configurable via env vars. See [FLARE_INTEGRATION.md](./FLARE_INTEGRATION.md) for the full variable list.

For full Flare integration documentation including FTSO feed IDs, contract addresses, and architecture diagrams see **[FLARE_INTEGRATION.md](./FLARE_INTEGRATION.md)**.
