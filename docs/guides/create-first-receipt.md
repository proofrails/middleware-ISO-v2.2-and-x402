# Create Your First Receipt

This guide walks through creating a receipt for an on-chain payment and verifying its evidence bundle.

## Prerequisites

- ProofRails running locally or deployed
- A project and API key (see [Quickstart](./quickstart-local.md))

## 1. Create a receipt

```bash
curl -X POST http://localhost:8000/v1/receipts \
  -H "X-API-Key: <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "reference": "invoice-2026-001",
    "tip_tx_hash": "0xabc123def456",
    "chain": "flare",
    "amount": "100.0",
    "currency": "FLR",
    "sender_wallet": "0xSenderAddress",
    "receiver_wallet": "0xReceiverAddress"
  }'
```

Response:

```json
{
  "id": "<receipt_uuid>",
  "reference": "invoice-2026-001",
  "status": "pending",
  "bundle_hash": null,
  "flare_txid": null,
  "created_at": "2026-04-30T12:00:00Z"
}
```

The receipt starts as `pending`. Background jobs generate the ISO XML, assemble the bundle, and anchor the hash on Flare.

## 2. Poll for completion

```bash
curl http://localhost:8000/v1/iso/receipts/<receipt_id>/status \
  -H "X-API-Key: <your_api_key>"
```

```json
{
  "id": "<receipt_uuid>",
  "status": "anchored",
  "bundle_hash": "0x1a2b3c...",
  "flare_txid": "0xdeadbeef...",
  "anchored_at": "2026-04-30T12:00:05Z"
}
```

Typical anchoring time: 5–30 seconds depending on Flare block time.

## 3. Get the full receipt

```bash
curl http://localhost:8000/v1/iso/receipts/<receipt_id> \
  -H "X-API-Key: <your_api_key>"
```

Returns the full record including `bundle_url`, `xml_url`, and anchor data.

## 4. Verify the bundle

```bash
curl -X POST http://localhost:8000/v1/iso/verify \
  -H "X-API-Key: <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"bundle_hash": "0x1a2b3c..."}'
```

## 5. Download the ISO XML

```bash
curl <bundle_url> -o bundle.zip
unzip bundle.zip
# View pain001.xml, pacs008.xml, camt054.xml, metadata.json, manifest.json
```

## Using the Python SDK

```python
from iso_middleware_sdk import ISOClient

client = ISOClient(base_url="http://localhost:8000", api_key="your_api_key")

# Create receipt
receipt = client.list_receipts(page=1, page_size=1)  # or via direct POST

# Poll status
import time
for _ in range(30):
    status = client.get_receipt_status(receipt_id)
    if status["status"] == "anchored":
        break
    time.sleep(2)

# Verify
result = client.verify_bundle(bundle_hash=status["bundle_hash"])
print(result["matches_onchain"])  # True
```

## See also

- [Verify an Evidence Bundle](./verify-evidence-bundle.md)
- [API: Receipts](../api/receipts.md)
- [Receipt Lifecycle](../architecture/receipt-lifecycle.md)
