# Verify an Evidence Bundle

This guide covers how to verify that an evidence bundle is authentic and that its hash matches the on-chain anchor.

## What verification proves

Verification confirms:

1. The bundle has not been modified since it was anchored.
2. The bundle hash was recorded on Flare before the anchor block timestamp.

It does not prove that the ISO content is accurate — that is the platform's responsibility to ensure at generation time.

## Via API

```bash
# Verify by bundle hash
curl -X POST /v1/iso/verify \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"bundle_hash": "0x1a2b3c..."}'

# Verify by bundle URL
curl -X POST /v1/iso/verify \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"bundle_url": "https://storage.example.com/bundles/abc.zip"}'
```

Response:

```json
{
  "matches_onchain": true,
  "bundle_hash": "0x1a2b3c...",
  "flare_txid": "0xdeadbeef...",
  "anchored_at": "2026-04-30T12:00:00Z"
}
```

## Via premium endpoint (x402)

```bash
curl -X POST /v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -H 'X-PAYMENT: {"tx_hash":"0x...","amount":"0.001","recipient":"0x...","currency":"USDC","chain":"base"}' \
  -d '{"bundle_hash": "0x1a2b3c..."}'
```

## Independently (no API)

Anyone can verify without trusting ProofRails:

### Step 1: Download the bundle

```bash
curl -O https://storage.example.com/bundles/bundle-<receipt_id>.zip
```

### Step 2: Compute the hash

```bash
sha256sum bundle-<receipt_id>.zip
# or
openssl dgst -sha256 bundle-<receipt_id>.zip
```

### Step 3: Query the Flare anchor contract

```bash
# Using cast (Foundry)
cast call <ANCHOR_CONTRACT_ADDRESS> \
  "verify(bytes32)(bool,uint256)" \
  <0x-prefixed-hash> \
  --rpc-url https://flare-api.flare.network/ext/C/rpc
```

Returns `(true, <block_timestamp>)` if anchored, reverts if not found.

## Via IPFS/Arweave CID

If the bundle was stored on IPFS or Arweave:

```bash
curl -X POST /v1/iso/verify-cid \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"cid": "Qm...", "store": "ipfs"}'
```

## See also

- [Evidence Bundles concept](../concepts/evidence-bundles.md)
- [API: Verification](../api/verification.md)
