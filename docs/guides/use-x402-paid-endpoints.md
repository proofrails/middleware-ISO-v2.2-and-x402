# Use x402 Paid Endpoints

This guide shows how to access payment-gated premium API endpoints using x402 micropayments on either Base (USDC) or Flare (FLR).

## How it works

Premium endpoints return `HTTP 402` if no payment header is present. The 402 body lists accepted payment options (USDC on Base and FLR on Flare). The client sends payment on the preferred chain, then retries with the transaction hash in the `X-PAYMENT` header.

## Development mode

For local development, set `X402_MOCK_PAYMENTS=true` in your environment. This bypasses on-chain verification so you can test without real funds.

**Never set this in production.**

## 1. Call a premium endpoint to see the 402 response

```bash
curl -X POST http://localhost:8000/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR", "provider": "ftso"}'
```

Response:

```json
HTTP/1.1 402 Payment Required
x-payment-required: true

{
  "error": "payment_required",
  "message": "This endpoint requires a micropayment",
  "accepted": [
    {
      "amount": "0.0005",
      "currency": "USDC",
      "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
      "chain": "base"
    },
    {
      "amount": "0.05",
      "currency": "FLR",
      "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
      "chain": "flare"
    }
  ]
}
```

## 2a. Pay with USDC on Base (ethers v6)

```typescript
import { JsonRpcProvider, Wallet, Contract, parseUnits } from "ethers";

const ERC20_ABI = ["function transfer(address to, uint256 amount) returns (bool)"];

const provider = new JsonRpcProvider(process.env.BASE_RPC_URL);
const signer = new Wallet(process.env.WALLET_PRIVATE_KEY!, provider);
const usdc = new Contract(process.env.USDC_CONTRACT!, ERC20_ABI, signer);

const tx = await usdc.transfer(
  "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  parseUnits("0.0005", 6),   // USDC has 6 decimals
);
await tx.wait(1);

const payment = JSON.stringify({
  tx_hash: tx.hash,
  amount: "0.0005",
  recipient: "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  currency: "USDC",
  chain: "base",
});
```

## 2b. Pay with FLR on Flare (ethers v6)

```typescript
import { JsonRpcProvider, Wallet, parseEther } from "ethers";

const provider = new JsonRpcProvider(process.env.FLARE_RPC_URL);
const signer = new Wallet(process.env.WALLET_PRIVATE_KEY!, provider);

const tx = await signer.sendTransaction({
  to: "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  value: parseEther("0.05"),   // FLR is 18 decimals
});
await tx.wait(1);

const payment = JSON.stringify({
  tx_hash: tx.hash,
  amount: "0.05",
  recipient: "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  currency: "FLR",
  chain: "flare",
});
```

## 3. Retry with X-PAYMENT header

```bash
# USDC on Base
curl -X POST http://localhost:8000/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xabc...","amount":"0.0005","recipient":"0x0690...","currency":"USDC","chain":"base"}' \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR", "provider": "ftso"}'

# FLR on Flare
curl -X POST http://localhost:8000/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xdef...","amount":"0.05","recipient":"0x0690...","currency":"FLR","chain":"flare"}' \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR", "provider": "ftso"}'
```

## 4. Mock mode (dev/test only)

```bash
X402_MOCK_PAYMENTS=true

curl -X POST http://localhost:8000/v1/x402/premium/fx-lookup \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xdead0001","amount":"0.0005","recipient":"0x0690...","currency":"USDC","chain":"base"}' \
  -d '{"base_ccy": "USD", "quote_ccy": "FLR", "provider": "ftso"}'
```

## Available premium endpoints

| Endpoint | Body | USDC | FLR |
|----------|------|------|-----|
| `POST /v1/x402/premium/verify-bundle` | `{"bundle_hash": "0x..."}` | 0.001 | 0.05 |
| `POST /v1/x402/premium/generate-statement` | `{"date": "2026-01-01"}` | 0.005 | 0.25 |
| `POST /v1/x402/premium/fx-lookup` | `{"base_ccy": "USD", "quote_ccy": "FLR", "provider": "ftso"}` | 0.0005 | 0.05 |
| `POST /v1/x402/premium/bulk-verify` | `{"bundle_urls": ["https://..."]}` | 0.01 | 0.50 |
| `POST /v1/x402/premium/refund` | `{"original_receipt_id": "..."}` | 0.001 | 0.15 |

Current pricing: `GET /v1/x402/pricing`

## Using the XMTP agent

The XMTP agent handles payment automatically using whichever chain its wallet is configured for. See [Deploy XMTP Agent](./deploy-xmtp-agent.md).

## See also

- [x402 Payments concept](../concepts/x402-payments.md)
- [API: x402](../api/x402.md)
- [Deploy XMTP Agent](./deploy-xmtp-agent.md)
