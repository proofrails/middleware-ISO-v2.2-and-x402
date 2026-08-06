# Deploy XMTP Agent

This guide covers deploying the ProofRails XMTP agent — the reference implementation of an AI agent that listens for XMTP messages and executes ISO 20022 and x402 operations.

## Prerequisites

- Node.js 18+
- A ProofRails backend (local or deployed)
- An EVM wallet with USDC on Base for x402 payments
- An XMTP-compatible wallet (same wallet is fine)

## 1. Install dependencies

```bash
cd agents/iso-x402-agent
npm install
```

## 2. Configure environment

```bash
cp .env.example .env
```

Required variables:

```env
# Agent wallet (used for XMTP identity and x402 payments)
AGENT_PRIVATE_KEY=0x<hex_private_key>

# XMTP network
XMTP_ENV=production   # or "dev" for testing

# ProofRails backend
ISO_MW_API_URL=https://your-backend.com
ISO_MW_API_KEY=your_api_key

# x402 payment target
X402_RECIPIENT=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
CHAIN_RPC_URL=https://mainnet.base.org
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Agent registration (get this from POST /v1/agents)
AGENT_ID=<uuid>

# Development mode — REMOVE IN PRODUCTION
# X402_MOCK_PAYMENTS=true
```

## 3. Register the agent in ProofRails

```bash
curl -X POST $ISO_MW_API_URL/v1/agents \
  -H "X-API-Key: $ISO_MW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "XMTP Agent",
    "wallet_address": "<agent_evm_address>"
  }'
```

Copy the returned `id` into `AGENT_ID` in `.env`.

## 4. Start the agent

```bash
npm start
```

The agent:
1. Connects to XMTP with the configured wallet.
2. Logs its XMTP address — share this with users.
3. Listens for inbound messages and processes commands.

## 5. Available commands

Send these as plain text messages to the agent's XMTP address:

```
help                          List commands
list                          List 10 most recent receipts
list 25                       List 25 most recent receipts
get <receipt_id>              Get receipt details
verify <bundle_url>           Verify an evidence bundle (costs 0.001 USDC)
statement 2026-01-01          Generate statement for a date (costs 0.005 USDC)
refund <receipt_id>           Initiate a refund (costs 0.001 USDC)
status <receipt_id>           Lightweight status check (no x402)
anchor {"key":"value"}        Hash and anchor JSON data on Flare (costs 0.001 USDC)
list anchors                  List recent anchor records
list anchors 14               List last 14 days of anchors
verify anchor 0xabc...        Check whether a hash is confirmed
```

## 6. AI mode (optional)

Set `ai_mode` on the agent for more flexible command parsing:

- `simple` (default): Fast pattern matching, no API calls.
- `shared`: Uses the ProofRails backend AI parser.
- `custom`: Uses a configured external model (OpenAI, Anthropic, etc.).

Configure via:

```bash
curl -X PUT $ISO_MW_API_URL/v1/agents/$AGENT_ID/ai-config \
  -H "X-API-Key: $ISO_MW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ai_mode": "shared"}'
```

## 7. Deploy with Docker

```bash
docker build -t proofrails-agent .
docker run -d --env-file .env proofrails-agent
```

Or use the provided `docker-compose.yml`:

```bash
docker-compose -f docker-compose.demo.yml up -d agent
```

## Known limitations

- The XMTP agent uses `@xmtp/xmtp-js` v7, which requires the V2 XMTP network. XMTP V3 (MLS) support is planned.
- The agent must run continuously; there is no message queue persistence between restarts.
- `verify`, `statement`, and `anchor` commands require sufficient USDC on Base.

## See also

- [Agentic Workflows](../concepts/agentic-workflows.md)
- [Configure Agent Anchoring](./configure-agent-anchoring.md)
- [Use x402 Paid Endpoints](./use-x402-paid-endpoints.md)
