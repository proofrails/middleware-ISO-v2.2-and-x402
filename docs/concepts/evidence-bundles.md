# Evidence Bundles

An evidence bundle is a ZIP archive that packages everything needed to independently verify that a specific on-chain payment happened and that the ISO record faithfully represents it.

## Contents

```
bundle-{receipt_id}.zip
├── pain001.xml        ISO 20022 credit transfer initiation
├── pacs008.xml        Settlement message (generated on confirmation)
├── camt054.xml        Debit/credit notification
├── metadata.json      Chain data: tx_hash, block_number, timestamp, chain_id
└── manifest.json      SHA-256 hashes of all files in the bundle
```

## Bundle hash

The bundle hash is `SHA-256(bundle.zip)` encoded as a lowercase `0x`-prefixed hex string. This hash is:

1. Stored in the `Receipt` database record (`bundle_hash` field).
2. Anchored on-chain by writing it to the ProofRails anchor contract on Flare.
3. Returned in the receipt API response.

## Verification

Anyone with the bundle and the on-chain anchor can verify:

1. Compute `SHA-256(bundle.zip)` independently.
2. Query the anchor contract on Flare with the hash.
3. The contract returns the block timestamp when the hash was anchored, or reverts if not found.

This is a one-way proof: if the hash matches the anchor, the bundle existed before the anchor timestamp and has not been modified. It does not prove correctness of the ISO content — that is the platform's responsibility.

## Bundle lifecycle

```
on_chain_tx detected
    → pain.001 generated
    → bundle assembled
    → bundle_hash computed
    → receipt created (status: pending)
    → anchor contract called (background task)
    → receipt updated (status: anchored, flare_txid set)
```

## API access

| Endpoint | Description |
|----------|-------------|
| `GET /v1/iso/receipts/{id}` | Returns receipt with `bundle_url` |
| `POST /v1/iso/verify` | Verify bundle by URL or hash |
| `POST /v1/iso/verify-cid` | Verify by IPFS/Arweave CID |
| `GET /v1/anchors/{receipt_id}` | List per-chain anchor txids |

## See also

- [Verification Guide](../guides/verify-evidence-bundle.md)
- [Receipt Lifecycle](../architecture/receipt-lifecycle.md)
- [API: Verification](../api/verification.md)
