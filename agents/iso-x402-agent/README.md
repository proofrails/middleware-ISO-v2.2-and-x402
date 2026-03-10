# ISO Middleware XMTP Agent

Autonomous AI agent for ISO 20022 payment processing with x402 micropayments and XMTP messaging.

## Features

✅ **Natural Language Processing** - Simple commands or AI-powered parsing  
✅ **Automatic Payments** - x402 protocol handles USDC micropayments  
✅ **XMTP Messaging** - Decentralized, encrypted communication  
✅ **Multi-Mode AI** - Choose simple, shared (free), or custom AI  
✅ **Multi-Chain** - USDC payments on Base chain  
✅ **One-Click Deploy** - Railway, Heroku, Docker support  

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
WALLET_PRIVATE_KEY=0x...        # Your agent's wallet
ISO_MW_API_URL=http://...       # ISO Middleware API
ISO_MW_API_KEY=your_key         # Optional API key
```

### 3. Build & Run

```bash
npm run build
npm start
```

## AI Configuration

The agent supports three AI modes:

### Simple Mode (Default)
- No AI - exact command matching only
- FREE - no API costs
- Fast response time
- Commands: `list 5`, `get abc123`, `verify https://...`

### Shared AI Mode (Recommended)
- Uses system OpenAI API (FREE for you!)
- Natural language understanding
- Custom system prompts supported
- Example: "Can you show me my recent receipts?"

### Custom AI Mode
- Use your own OpenAI/Claude/Gemini API key
- Full privacy and control
- Your billing, your rules
- Advanced customization

Configure via:
1. UI: http://localhost:3000/agents → Select agent → AI Settings
2. API: `PUT /v1/agents/{id}/ai-config`

## Deployment Options

### Option 1: PM2 (Recommended for VPS)

```bash
npm install -g pm2
npm run build
pm2 start dist/index.js --name iso-agent
pm2 save
pm2 startup
```

### Option 2: Docker

```bash
docker-compose up -d
```

Or build manually:
```bash
docker build -t iso-agent .
docker run -d --env-file .env --name iso-agent iso-agent
```

### Option 3: Railway (One-Click)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/your-repo)

Or manually:
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Option 4: Heroku

```bash
heroku create iso-agent
heroku config:set WALLET_PRIVATE_KEY=0x...
git push heroku main
heroku ps:scale worker=1
```

## Usage

### Connect via XMTP

**Using Converse App (Mobile):**
1. Install Converse from App Store
2. Create/import wallet
3. Start conversation with agent address
4. Send commands!

**Available Commands:**

```
# Free commands
list [limit]              - List receipts
get <receipt_id>          - Get receipt details
help                      - Show help

# Paid commands (auto-payment via x402)
verify <bundle_url>       - Verify bundle (0.001 USDC)
statement <date>          - Generate statement (0.005 USDC)
refund <receipt_id>       - Initiate refund (0.003 USDC)
```

### Example Conversations

**Simple Mode:**
```
You: list 5
Agent: 📋 Recent Receipts (5): ...
```

**AI Mode:**
```
You: Can you verify if this bundle is valid? https://ipfs.io/ipfs/Qm...
Agent: ⏳ Verifying bundle (paying 0.001 USDC)...
       ✅ Valid! Hash: 0x1234...
```

## Configuration

### Environment Variables

```bash
# Required
WALLET_PRIVATE_KEY=0x...
ISO_MW_API_URL=http://localhost:8000

# Optional
XMTP_ENV=dev                    # or 'production'
ISO_MW_API_KEY=key              # API authentication
X402_RECIPIENT=0x...            # Payment recipient
AGENT_NAME=My Agent             # Display name
LOG_LEVEL=info                  # debug, info, warn, error

# AI (Optional)
AI_MODE=simple                  # simple | shared | custom
AI_SYSTEM_PROMPT=Custom...      # For shared/custom mode
AI_PROVIDER=openai              # For custom mode
AI_API_KEY=sk-...               # For custom mode
AI_MODEL=gpt-4o-mini            # For custom mode
```

## Monitoring

### Check Agent Status

```bash
# PM2
pm2 status
pm2 logs iso-agent

# Docker
docker logs -f iso-agent

# Railway/Heroku
railway logs
heroku logs --tail
```

### Track Spending

View in UI: http://localhost:3000/agents → Select agent → Stats

Or via API:
```bash
curl http://localhost:8000/v1/agents/{id}/stats?days=7
```

## Security

### Best Practices

1. **Wallet Security**
   - Use dedicated wallet for agent
   - Keep minimal USDC balance (1-10 USDC)
   - Rotate keys regularly

2. **Environment Variables**
   - Never commit `.env`
   - Use secrets management in production
   - Encrypt sensitive values

3. **API Keys**
   - Rotate periodically
   - Use separate keys per environment
   - Monitor usage

## Troubleshooting

### Agent Won't Start

```bash
# Check logs
pm2 logs iso-agent --lines 100

# Verify configuration
cat .env

# Test XMTP connection
node -e "console.log(require('ethers').Wallet.createRandom().address)"
```

### Payment Failures

```bash
# Check USDC balance
# Base chain explorer: https://basescan.org

# Verify recipient address
echo $X402_RECIPIENT

# Test payment endpoint
curl -X POST http://localhost:8000/v1/x402/verify-payment \
  -H "Content-Type: application/json" \
  -d '{"tx_hash":"0xtest","amount":"0.001","recipient":"0x..."}'
```

### XMTP Connection Issues

```bash
# Try different environment
XMTP_ENV=production npm start

# Check wallet has funds for gas
# Verify private key format (0x prefix)
```

## Development

### Local Testing

```bash
npm run dev
```

### Add Custom Commands

1. Update `src/utils/parser.ts`:
```typescript
if (trimmed.startsWith('custom ')) {
  return { action: 'custom', args: {...} };
}
```

2. Create handler in `src/handlers/custom.ts`

3. Register in `src/agent.ts`

## Support

- **Documentation**: ../../docs/AGENTS_GUIDE.md
- **API Docs**: http://localhost:8000/docs
- **UI**: http://localhost:3000/agents
- **GitHub Issues**: [repository]/issues

## License

MIT
