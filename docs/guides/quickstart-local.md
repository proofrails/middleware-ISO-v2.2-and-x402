# Quickstart: Local Development

This guide gets ProofRails running locally in under 10 minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for PostgreSQL)

## 1. Clone and install

```bash
git clone https://github.com/proofrails/middleware-ISO-v2.2-and-x402.git
cd middleware-ISO-v2.2-and-x402

# Python backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend (optional)
cd web-alt && npm install && cd ..
```

## 2. Configure environment

```bash
cp .env.example .env
```

Minimum required settings in `.env`:

```env
# Database — SQLite is fine for local dev
DATABASE_URL=sqlite:///./local.db
AUTO_CREATE_DB=true

# Anchoring (optional for local dev)
# FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
# ANCHOR_CONTRACT=0x...
# ANCHOR_PRIVATE_KEY=0x...

# x402 payment verification
# Set to true only for local development/testing
X402_MOCK_PAYMENTS=true

# Rate limiting — disable for local dev
RATE_LIMIT_ENABLED=false
IDEMPOTENCY_ENABLED=false
```

## 3. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

## 4. Run tests

```bash
pytest tests/ -q
```

Expected: 100+ tests pass in under 5 seconds (all in-process, no external dependencies).

## 5. Start the frontend (optional)

```bash
cd web-alt
cp .env.production.example .env.local
# Edit NEXT_PUBLIC_API_BASE if your backend is not on port 8000
npm run dev
```

Frontend at `http://localhost:3000`.

## 6. Register a project and create your first receipt

```bash
# Create a project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "owner_wallet": "0xYourWallet"}'

# Note the returned project_id and api_key

# Create a receipt
curl -X POST http://localhost:8000/v1/receipts \
  -H "X-API-Key: <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "reference": "test-001",
    "tip_tx_hash": "0xabc123",
    "chain": "flare",
    "amount": "10.5",
    "currency": "FLR",
    "sender_wallet": "0xSender",
    "receiver_wallet": "0xReceiver"
  }'
```

## Next steps

- [Create Your First Receipt](./create-first-receipt.md)
- [Configure Agent Anchoring](./configure-agent-anchoring.md)
- [Use x402 Paid Endpoints](./use-x402-paid-endpoints.md)
