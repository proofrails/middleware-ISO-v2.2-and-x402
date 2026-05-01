# Example: Simple Flare Receipt

Create a receipt for a Flare C-Chain FLR transfer, wait for anchoring, and verify the evidence bundle.

## Python

```python
import time
from iso_middleware_sdk import ISOClient

client = ISOClient(
    base_url="http://localhost:8000",
    api_key="your_api_key",
)

# 1. Create receipt
# (In practice, tip_tx_hash comes from a real Flare transaction)
receipt = client.list_receipts()  # or via raw POST

# Simulate: POST directly
import requests
resp = requests.post(
    "http://localhost:8000/v1/receipts",
    headers={"X-API-Key": "your_api_key", "Content-Type": "application/json"},
    json={
        "reference": "flare-payment-001",
        "tip_tx_hash": "0xabc123def456789",
        "chain": "flare",
        "amount": "50.0",
        "currency": "FLR",
        "sender_wallet": "0xSenderWallet",
        "receiver_wallet": "0xReceiverWallet",
    },
)
receipt_id = resp.json()["id"]
print(f"Receipt created: {receipt_id}")

# 2. Poll for anchoring
for _ in range(30):
    status = client.get_receipt_status(receipt_id)
    print(f"Status: {status['status']}")
    if status["status"] in ("anchored", "failed"):
        break
    time.sleep(2)

# 3. Verify
result = client.verify_bundle(bundle_hash=status["bundle_hash"])
print(f"Matches on-chain: {result['matches_onchain']}")
print(f"Anchored at: {result['anchored_at']}")
print(f"Flare tx: {result['flare_txid']}")
```

## TypeScript

```typescript
import IsoMiddlewareClient from "iso-middleware-sdk";

const client = new IsoMiddlewareClient({
  baseUrl: "http://localhost:8000",
  apiKey: "your_api_key",
});

// Poll until anchored
async function waitForAnchor(receiptId: string, timeoutMs = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const status = await client.getReceiptStatus(receiptId);
    if (status.status === "anchored") return status;
    if (status.status === "failed") throw new Error("Anchoring failed");
    await new Promise(r => setTimeout(r, 2000));
  }
  throw new Error("Timeout waiting for anchor");
}

const receiptId = "..."; // from POST /v1/receipts
const status = await waitForAnchor(receiptId);
const result = await client.verifyBundle({ bundle_hash: status.bundle_hash! });
console.log("matches_onchain:", result.matches_onchain);
```

## Expected output

```
Receipt created: 3fa85f64-5717-4562-b3fc-2c963f66afa6
Status: pending
Status: pending
Status: anchored
Matches on-chain: True
Anchored at: 2026-04-30T12:00:07.123Z
Flare tx: 0xdeadbeef...
```
