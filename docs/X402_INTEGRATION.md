# x402 Protocol Integration Guide

This document covers the x402 micropayment protocol as implemented in the ISO 20022 Middleware — how it works, how to configure it, how agents pay for premium endpoints, and how to build on the x402-example contracts.

---

## What is x402?

The [x402 protocol](https://www.x402.org/) uses HTTP's long-reserved `402 Payment Required` status code to enable native payments on the web. When a client requests a premium endpoint without payment, the server returns 402 with machine-readable payment instructions. The client makes an on-chain USDC transfer, includes proof in the next request, and the server verifies the payment before serving the response.

This middleware uses x402 to gate premium API endpoints behind USDC micropayments on Base chain.

---

## How It Works

### Payment Flow

```
1. Client → Server:  GET /v1/x402/premium/verify-bundle
                     (no X-PAYMENT header)

2. Server → Client:  HTTP 402
                     {
                       "amount": "0.001",
                       "recipient": "0x0690...",
                       "currency": "USDC",
                       "chain": "base"
                     }
                     Headers:
                       X-Payment-Required: true
                       X-Payment-Amount: 0.001
                       X-Payment-Currency: USDC

3. Client:           Makes USDC transfer on Base chain → gets tx_hash

4. Client → Server:  POST /v1/x402/premium/verify-bundle
                     X-PAYMENT: {"tx_hash":"0x...","amount":"0.001","recipient":"0x0690..."}
                     Body: {"bundle_url": "https://..."}

5. Server:           Verifies tx on-chain (checks Transfer event, amount, recipient)
                     Records payment in x402_payments table
                     Executes endpoint logic

6. Server → Client:  HTTP 200 + result
                     X-Payment-Response: {"verified":true,"tx_hash":"0x...","amount":"0.001"}
```

### On-Chain Verification

The `X402PaymentVerifier` class in `app/x402.py` verifies payments by:

1. Fetching the transaction receipt from Base chain via `BASE_RPC_URL`.
2. Checking that the transaction succeeded (status = 1).
3. Scanning logs for an ERC-20 `Transfer` event from the USDC contract (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` on Base mainnet).
4. Verifying the `to` address matches the expected recipient.
5. Decoding the transfer amount (USDC has 6 decimals) and checking it matches the expected amount within a 0.0001 USDC tolerance.

---

## Premium Endpoints

Six endpoints are gated behind x402 payments:

| Endpoint | Method | Price | Description |
|----------|--------|-------|-------------|
| `/v1/x402/premium/verify-bundle` | POST | 0.001 USDC | Verify evidence bundle integrity and on-chain status |
| `/v1/x402/premium/generate-statement` | POST | 0.005 USDC | Generate camt.052 (intraday) or camt.053 (daily) statement |
| `/v1/x402/premium/iso-message/{receipt_id}/{type}` | GET | 0.002 USDC | Retrieve a specific ISO message artifact |
| `/v1/x402/premium/fx-lookup` | POST | 0.001 USDC | Foreign exchange rate lookup |
| `/v1/x402/premium/bulk-verify` | POST | 0.010 USDC | Verify multiple bundles in one request |
| `/v1/x402/premium/refund` | POST | 0.003 USDC | Initiate a payment refund |

Pricing is also stored in the `protected_endpoints` database table and can be updated dynamically via `POST /v1/x402/pricing` (admin only).

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `X402_RECIPIENT_ADDRESS` | `0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8` | Address that receives USDC payments |
| `BASE_RPC_URL` | `https://mainnet.base.org` | Base chain RPC for payment verification |
| `X402_USDC_ADDRESS` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | USDC contract on Base mainnet |

### Dynamic Pricing

Update endpoint prices at runtime:

```bash
curl -X POST http://localhost:8000/v1/x402/pricing \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '[
    {"path": "/v1/x402/premium/verify-bundle", "price": "0.002", "recipient": "0x0690..."},
    {"path": "/v1/x402/premium/fx-lookup", "price": "0.0005", "recipient": "0x0690...", "enabled": "true"}
  ]'
```

---

## Making Payments (Client Side)

### X-PAYMENT Header Format

The payment proof is a JSON object passed in the `X-PAYMENT` request header:

```json
{
  "tx_hash": "0xTransactionHash...",
  "amount": "0.001",
  "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  "currency": "USDC",
  "chain": "base",
  "timestamp": "2026-01-20T20:00:00Z"
}
```

### TypeScript Example

```typescript
import { ethers } from 'ethers';

const USDC_ABI = ['function transfer(address to, uint256 amount) returns (bool)'];
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

async function payAndRequest(endpoint: string, price: string, body: any) {
  const provider = new ethers.JsonRpcProvider('https://mainnet.base.org');
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
  const usdc = new ethers.Contract(USDC_ADDRESS, USDC_ABI, wallet);

  // 1. Transfer USDC (6 decimals)
  const amount = ethers.parseUnits(price, 6);
  const tx = await usdc.transfer('0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8', amount);
  const receipt = await tx.wait();

  // 2. Build payment header
  const paymentHeader = JSON.stringify({
    tx_hash: receipt.hash,
    amount: price,
    recipient: '0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8',
    currency: 'USDC',
    chain: 'base',
  });

  // 3. Make paid request
  const response = await fetch(`http://localhost:8000${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-PAYMENT': paymentHeader,
    },
    body: JSON.stringify(body),
  });

  return response.json();
}

// Usage
const result = await payAndRequest(
  '/v1/x402/premium/verify-bundle',
  '0.001',
  { bundle_url: 'https://ipfs.io/ipfs/Qm...' }
);
```

### Python Example

```python
from web3 import Web3
import requests
import json

USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
RECIPIENT = '0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8'
USDC_ABI = [{"name":"transfer","type":"function","inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],"outputs":[{"type":"bool"}]}]

def pay_and_request(endpoint, price, body):
    w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    usdc = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)

    # 1. Transfer USDC
    amount = int(float(price) * 1e6)  # 6 decimals
    tx = usdc.functions.transfer(RECIPIENT, amount).transact({'from': account.address})
    receipt = w3.eth.wait_for_transaction_receipt(tx)

    # 2. Make paid request
    payment_header = json.dumps({
        'tx_hash': receipt.transactionHash.hex(),
        'amount': price,
        'recipient': RECIPIENT,
        'currency': 'USDC',
        'chain': 'base',
    })

    response = requests.post(
        f'http://localhost:8000{endpoint}',
        json=body,
        headers={'X-PAYMENT': payment_header},
    )
    return response.json()
```

---

## The `@require_payment` Decorator

The middleware uses a Python decorator to gate endpoints:

```python
from app.x402 import require_payment

@require_payment("0.001", "0xRecipientAddress")
@router.post("/v1/x402/premium/my-endpoint")
async def my_premium_endpoint(request: Request):
    return {"data": "premium content"}
```

The decorator:

1. Checks for the `X-PAYMENT` header. If absent, returns HTTP 402 with payment details.
2. Parses the payment proof JSON.
3. Calls `verify_payment()` to check the transaction on-chain.
4. If invalid, returns 403.
5. Records the payment in the `x402_payments` table (best-effort).
6. Executes the endpoint function.
7. Adds `X-Payment-Response` header to the response.

---

## Payment Analytics

### `GET /v1/x402/payments`

List verified payments (requires authentication):

```json
[
  {
    "tx_hash": "0xabc...",
    "amount": "0.001",
    "currency": "USDC",
    "chain": "base",
    "recipient": "0x0690...",
    "endpoint": "premium_verify_bundle",
    "verified_at": "2026-01-20T20:00:00Z"
  }
]
```

### `GET /v1/x402/pricing`

List all gated endpoints and their current prices.

---

## x402-Example: EIP-3009 Implementation

The `Downloads/x402-example-main/` directory contains a standalone demo of the x402 protocol using EIP-3009 `transferWithAuthorization` for gasless settlements on Flare's Coston2 testnet.

### Contracts

**MockUSDT0** (`contracts/MockUSDT0.sol`): ERC-20 token with full EIP-3009 support, including `transferWithAuthorization`, `receiveWithAuthorization` (front-running protected), and `DOMAIN_SEPARATOR()`.

**X402Facilitator** (`contracts/X402Facilitator.sol`): Verifies and settles EIP-3009 payment authorizations. Methods: `verifyPayment()`, `settlePayment()`, `settlePaymentAsPayee()`.

### EIP-3009 Flow

Unlike standard ERC-20 transfers, EIP-3009 allows the *payer* to sign an off-chain EIP-712 authorization. The *server* (or facilitator contract) then calls `transferWithAuthorization` to execute the transfer — meaning the payer never needs to send a transaction or pay gas.

```
Agent signs EIP-712 authorization (off-chain, gasless)
     ↓
Server calls X402Facilitator.settlePayment(authorization)
     ↓
Facilitator calls MockUSDT0.transferWithAuthorization(from, to, value, ...)
     ↓
Tokens move from Agent → Server
```

### EIP-712 Signature Structure

```typescript
const domain = {
  name: "Mock USDT0",
  version: "1",
  chainId: 114,  // Coston2
  verifyingContract: tokenAddress
};

const types = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" }
  ]
};
```

### Running the Example

```bash
cd Downloads/x402-example-main/x402-example-main

# Deploy contracts to Coston2
yarn hardhat run scripts/deploy.ts --network coston2

# Test EIP-3009 directly
yarn hardhat run scripts/testEip3009.ts --network coston2

# Start the server (port 3402)
npx ts-node scripts/server.ts

# Run the agent
npx ts-node scripts/testFlow.ts
```

The server exposes three endpoints: `GET /api/public` (free), `GET /api/premium-data` (0.1 USDT0), and `GET /api/report` (0.5 USDT0).

---

## Integration with Agent Anchoring

When an agent has `anchor_on_payment: true` configured, each x402 payment triggers an automatic anchor:

1. Agent sends a paid request (e.g., verify a bundle for 0.001 USDC).
2. The middleware verifies the payment and executes the endpoint.
3. A background task creates an `AgentAnchor` record with the payment data hash.
4. The anchor worker sends the hash to the `EvidenceAnchor` contract.
5. The anchor poller confirms the transaction.

This creates an immutable on-chain record tying the payment to the operation performed.

---

## Security Considerations

1. **Payment replay prevention**: Each transaction hash can only be used once. The `x402_payments` table has a unique constraint on `tx_hash`.

2. **Amount tolerance**: Verification allows a 0.0001 USDC variance to account for gas rounding.

3. **Time bounds**: When using EIP-3009, set reasonable `validAfter` / `validBefore` windows (recommended: 60 seconds before now to 5 minutes after now).

4. **Nonce randomness**: Always use cryptographically random 32-byte nonces for EIP-3009 authorizations.

5. **Front-running**: For contract-to-contract settlements, prefer `receiveWithAuthorization` over `transferWithAuthorization` as it can only be called by the designated recipient.
