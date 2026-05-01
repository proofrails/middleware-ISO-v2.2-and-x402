# Architecture: Receipt Lifecycle

## State machine

```
         POST /v1/receipts
               │
               ▼
           [pending]
               │
               ├── ISO XML generation
               │     pain.001, pacs.008, camt.054 written to disk
               │
               ├── Bundle assembly
               │     ZIP: ISO XMLs + metadata.json + manifest.json
               │
               ├── Hash computation
               │     bundle_hash = sha256(bundle.zip)
               │
               ├── Background task: call anchor contract
               │     anchor_module.anchor_bundle(bundle_hash)
               │
               ▼
           [anchored]  ←── flare_txid set, anchored_at set
               │
               └── (or) [failed]  ←── anchor tx reverted / RPC error
```

## Database fields

| Field | Set when |
|-------|---------|
| `id` | At creation |
| `status` | `pending` at creation, updated by background task |
| `bundle_hash` | When bundle is assembled |
| `bundle_path` | When bundle is written to disk |
| `xml_path` | When ISO XML is written |
| `flare_txid` | When anchor transaction is mined |
| `anchored_at` | When anchor confirmed |

## Background task isolation

The anchor submission runs as a FastAPI `BackgroundTask`. If it fails:
- `receipt.status` is set to `failed`
- The failure is logged with `receipt_id` and exception
- The receipt can be re-anchored by calling `POST /v1/iso/confirm-anchor` with the transaction ID

## Multi-chain anchoring

Projects can configure multiple chains in their project config:

```json
{
  "anchoring": {
    "execution_mode": "platform",
    "chains": [
      { "name": "flare", "contract": "0x...", "rpc_url": "..." },
      { "name": "coston2", "contract": "0x...", "rpc_url": "..." }
    ]
  }
}
```

Each chain gets its own `ChainAnchor` record. The `flare_txid` on the receipt always refers to the primary (first) chain anchor.

## Tenant execution mode

When `execution_mode: "tenant"`, the platform does not submit anchors. The project calls:

```
POST /v1/iso/confirm-anchor
{
  "receipt_id": "<uuid>",
  "flare_txid": "0x...",
  "chain": "flare"
}
```

## ISO artifact types stored

| Type | Message | Generated |
|------|---------|---------|
| `pain.001` | Credit Transfer Initiation | At receipt creation |
| `pain.002` | Payment Status Report | At status change |
| `pain.008` | Direct Debit Initiation | If debit flow |
| `pacs.008` | FI-to-FI Credit Transfer | At settlement |
| `pacs.004` | Payment Return | For refunds |
| `camt.053` | Account Statement | Via statement endpoint |
| `camt.054` | Debit/Credit Notification | At anchoring |
| `remt.001` | Remittance Advice | When metadata includes remittance |
