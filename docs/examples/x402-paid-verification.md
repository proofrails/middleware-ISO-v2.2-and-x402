# Example: x402 Paid Verification

Verify an evidence bundle through the payment-gated premium endpoint.

This example shows the full x402 flow: receive a 402, pay, retry.

## TypeScript (using the XMTP agent client)

```typescript
import { ISOMiddlewareClient } from "../../agents/iso-x402-agent/src/x402/client";
import { Wallet } from "ethers";

const wallet = new Wallet(process.env.AGENT_PRIVATE_KEY!);

const client = new ISOMiddlewareClient({
  apiUrl: "http://localhost:8000",
  apiKey: "your_api_key",
  x402Recipient: "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  chainRpcUrl: process.env.BASE_RPC_URL!,
  usdcContract: process.env.USDC_CONTRACT!,
  wallet,
});

// The client handles payment automatically:
// 1. Calls the endpoint
// 2. If 402, reads pricing and sends USDC
// 3. Retries with X-PAYMENT header
const result = await client.verifyBundle("0x<bundle_hash>");
console.log(result);
```

## Manual flow (curl)

### Step 1: Get the 402

```bash
curl -X POST http://localhost:8000/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -d '{"bundle_hash": "0xabc123..."}'
```

Response:
```
HTTP/1.1 402 Payment Required
x-payment-required: true

{"accepted":[{"amount":"0.001","currency":"USDC","recipient":"0x...","chain":"base"}]}
```

### Step 2: Send USDC on Base

```bash
# Using cast (Foundry)
cast send <USDC_CONTRACT> \
  "transfer(address,uint256)" \
  0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8 \
  1000 \
  --rpc-url $BASE_RPC_URL \
  --private-key $WALLET_KEY
# Returns tx hash: 0x...
```

### Step 3: Retry with X-PAYMENT

```bash
curl -X POST http://localhost:8000/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xYOUR_TX","amount":"0.001","recipient":"0x0690...","currency":"USDC","chain":"base"}' \
  -d '{"bundle_hash": "0xabc123..."}'
```

Response:
```json
{
  "matches_onchain": true,
  "bundle_hash": "0xabc123...",
  "flare_txid": "0xdeadbeef...",
  "anchored_at": "2026-04-30T12:00:00Z"
}
```

## Development mode (no real USDC)

```bash
export X402_MOCK_PAYMENTS=true

curl -X POST http://localhost:8000/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0xdead0001","amount":"0.001","recipient":"0x0690...","currency":"USDC","chain":"base"}' \
  -d '{"bundle_hash": "0xabc123..."}'
```

**Never set `X402_MOCK_PAYMENTS=true` in production.**
