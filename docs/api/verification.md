# API: Verification

## Verify bundle

```
POST /v1/iso/verify
```

Verifies an evidence bundle by URL or hash.

Body:

```json
{
  "bundle_url": "https://...",
  "bundle_hash": "0x..."
}
```

At least one of `bundle_url` or `bundle_hash` is required. If both are provided, the URL is fetched and its hash is compared against the provided `bundle_hash`.

Response:

```json
{
  "matches_onchain": true,
  "bundle_hash": "0x1a2b3c...",
  "flare_txid": "0xdeadbeef...",
  "anchored_at": "2026-04-30T12:00:00Z"
}
```

`matches_onchain: false` means the hash was not found in the anchor contract. `matches_onchain: null` means the chain query failed (RPC unavailable).

## Verify by CID

```
POST /v1/iso/verify-cid
```

Verifies a bundle stored on IPFS or Arweave.

Body:

```json
{
  "cid": "Qm...",
  "store": "ipfs",
  "receipt_id": "<optional_uuid>"
}
```

`store` values: `ipfs`, `arweave`, `auto`.

## List chain anchors for a receipt

```
GET /v1/anchors/{receipt_id}
```

Returns per-chain anchor records:

```json
[
  {
    "chain": "flare",
    "txid": "0x...",
    "anchored_at": "2026-04-30T12:00:00Z"
  }
]
```

## Confirm anchor (tenant mode)

```
POST /v1/iso/confirm-anchor
```

Used when the project manages its own anchor contract (tenant execution mode).

Body:

```json
{
  "receipt_id": "<uuid>",
  "flare_txid": "0x...",
  "chain": "flare"
}
```

## See also

- [Evidence Bundles concept](../concepts/evidence-bundles.md)
- [Verify Evidence Bundle guide](../guides/verify-evidence-bundle.md)
