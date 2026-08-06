# API: Receipts

## List receipts

```
GET /v1/receipts
```

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `pending`, `anchored`, `failed` |
| `chain` | string | Filter by chain: `flare`, `base` |
| `reference` | string | Filter by reference (exact match) |
| `since` | ISO datetime | Created after this time |
| `until` | ISO datetime | Created before this time |
| `scope` | string | `mine` (default) or `all` (admin only) |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 20, max: 100) |

Response:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

## Get receipt

```
GET /v1/iso/receipts/{receipt_id}
```

Returns the full receipt with `bundle_url`, `xml_url`, anchor data, ISO artifact references, and any attached metadata.

## Get receipt status (lightweight)

```
GET /v1/iso/receipts/{receipt_id}/status
```

Returns `id`, `status`, `bundle_hash`, `flare_txid`, `anchored_at`. Does not return ISO XML URLs. Use for polling.

## Create receipt

```
POST /v1/receipts
```

Body:

```json
{
  "reference": "invoice-001",
  "tip_tx_hash": "0xabc123",
  "chain": "flare",
  "amount": "100.0",
  "currency": "FLR",
  "sender_wallet": "0x...",
  "receiver_wallet": "0x...",
  "extra_metadata": {},
  "tags": []
}
```

`tip_tx_hash` must be unique per chain. Duplicate submissions return 409.

## Initiate refund

```
POST /v1/iso/refund
```

Body:

```json
{
  "original_receipt_id": "<uuid>",
  "reason_code": "CUST"
}
```

Creates a new receipt linked to the original via `refund_of`. Generates pacs.004 return message.

## Generate statements

```
GET /v1/iso/statements/camt053?date=2026-01-01
GET /v1/iso/statements/camt052?date=2026-01-01&window=1h
```

Aggregates receipts for the given date/window into an account statement XML.

## Receipt lifecycle

`pending` → `anchored` (or `failed`)

See [Receipt Lifecycle](../architecture/receipt-lifecycle.md).
