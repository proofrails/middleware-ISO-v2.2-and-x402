# ProofRails XMTP Agent

An XMTP messaging agent that lets users interact with the ProofRails API via natural language. It handles ISO 20022 receipts, bundle verification, statements, refunds, and agent-triggered anchoring — with automatic x402 USDC micropayments for paid commands.

## Prerequisites

- Node.js 20+
- A funded EVM wallet (USDC on Base for paid commands)
- A running ProofRails backend (`ISO_MW_API_URL`)
- An agent record created in the backend (for `anchor` commands)

## Setup

```bash
npm install
cp .env.example .env
# Edit .env with your keys
npm run build
npm start
```

## Environment variables

```bash
# Required
WALLET_PRIVATE_KEY=0x...          # EVM wallet private key (funds x402 payments)
ISO_MW_API_URL=http://localhost:8000
X402_RECIPIENT=0x...              # Address that receives x402 payments

# Optional
ISO_MW_API_KEY=                   # API key for backend auth
AGENT_ID=                         # Agent ID from POST /v1/agents (required for anchor commands)
XMTP_ENV=dev                      # dev | production
CHAIN_RPC_URL=https://mainnet.base.org
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
AGENT_NAME=ISO Middleware Agent
LOG_LEVEL=info

# AI (optional — defaults to simple mode)
AI_MODE=simple                    # simple | shared | custom
AI_SYSTEM_PROMPT=                 # custom system prompt
AI_PROVIDER=openai                # openai | anthropic | google (custom mode)
AI_API_KEY=sk-...                 # API key (custom mode)
AI_MODEL=gpt-4o-mini              # model name (custom mode)
```

## Commands

Send any of the following to the agent's XMTP address:

```
help                          Show available commands

# Receipt commands (free)
list [limit]                  List recent receipts (default: 5)
get <receipt_id>              Get receipt details
status <receipt_id>           Poll receipt status (lightweight)

# Paid commands (auto-payment via x402 USDC)
verify <bundle_url>           Verify evidence bundle
statement <date>              Generate camt.053 statement (YYYY-MM-DD)
refund <receipt_id>           Initiate refund/return

# Anchoring commands (requires AGENT_ID)
anchor <json>                 Hash and anchor arbitrary JSON data
list anchors [days]           List recent anchor records (default: 7 days)
verify anchor <hash>          Verify an anchor hash exists on-chain
```

In AI mode (shared or custom), these can be expressed as natural language: "can you show me my last 10 receipts?" or "anchor this data: {key: value}".

## AI modes

| Mode | Description |
|------|-------------|
| `simple` | Exact command matching only. No API costs. (default) |
| `shared` | Uses the ProofRails system AI parser. Free for the agent operator. |
| `custom` | Your own OpenAI/Anthropic/Google key. Full control. |

Configure AI mode via `AI_MODE` env var or via the ProofRails UI at `/agents` > AI Settings.

## Deployment

### Docker

```bash
docker build -t iso-x402-agent .
docker run -d --env-file .env --name iso-x402-agent iso-x402-agent
```

### PM2

```bash
npm install -g pm2
npm run build
pm2 start dist/index.js --name iso-x402-agent
pm2 save && pm2 startup
```

### Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

## Getting an AGENT_ID

Create an agent record in the ProofRails backend before using `anchor` commands:

```bash
curl -X POST http://localhost:8000/v1/agents \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My XMTP Agent",
    "wallet_address": "0x<your_wallet>",
    "xmtp_address": "0x<xmtp_address>"
  }'
# Returns: {"id": "...", ...}  — use this as AGENT_ID
```

## Development

```bash
npm run dev          # ts-node watch mode
npx tsc --noEmit     # typecheck only
```

## License

MIT
