# Architecture: Flare Implementation

## Anchoring on Flare EVM

ProofRails anchors evidence bundle hashes on the Flare C-Chain via a simple anchor contract.

**Status: Implemented**

### Contract interface

```solidity
function store(bytes32 hash) external;
function verify(bytes32 hash) external view returns (bool exists, uint256 timestamp);
```

### Transaction flow

1. Backend calls `anchor_module.anchor_bundle(bundle_hash, private_key=...)`.
2. The anchor module constructs an EVM transaction to `store(bytes32)`.
3. Transaction is broadcast to `FLARE_RPC_URL`.
4. Backend polls for confirmation and stores `flare_txid`.

### Configuration

```env
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ANCHOR_CONTRACT=0x<contract_address>
ANCHOR_PRIVATE_KEY=0x<hex_key>
```

---

## FTSO v2 Price Feeds

ProofRails uses Flare's FTSO v2 for real-time FX rates in the `fx-lookup` premium endpoint and for amount normalisation in statements.

**Status: Implemented** (`app/flare/ftso.py`)

### Feed IDs used

| Pair | Feed ID |
|------|---------|
| FLR/USD | `0x464c522f555344...` |
| XRP/USD | `0x5852502f555344...` |

FTSO v2 feeds update every ~90 seconds. The client reads the latest value from the `FastUpdater` contract.

---

## Flare Data Connector (FDC)

FDC allows Flare to verify events on external chains (Bitcoin, XRP, Ethereum, Avalanche) by:
1. Collecting attestations from independent attestation providers.
2. Aggregating them into a Merkle tree published on Flare.
3. Providing a proof that any smart contract can verify.

**Status: Prototype design** — not yet wired into the receipt pipeline.

### Proposed integration

Use FDC to verify XRP Ledger payments before generating a receipt:

1. Client submits XRPL payment proof request.
2. ProofRails queries FDC attestation providers for the XRPL txid.
3. Once attestation threshold is met, receipt is generated using the verified data.
4. This eliminates the need for ProofRails to trust any single oracle.

---

## FAssets

FAssets wraps non-EVM assets (FXRP, FBTC, FDOGE) on Flare with EVM-compatible tokens backed by collateral.

**Status: Proposed** — not yet implemented.

### Proposed integration

- Monitor FAssets minting/redemption events.
- Generate pacs.008 messages for FXRP flows to/from Flare.
- Use the XRPL txid as the `EndToEndId` in the ISO message.

---

## Smart Accounts

Flare Smart Accounts allow XRPL users (identified by their XRPL public key) to interact with Flare EVM without a separate EVM wallet.

**Status: Proposed** — not yet implemented.

### Proposed integration

- XRPL users register their XRPL key via Smart Accounts.
- ProofRails maps XRPL address → Flare EVM address.
- Agent workflows can accept XRPL-signed commands and execute Flare transactions.

---

## See also

- [Flare-Native Implementations concepts](../concepts/flare-native-implementations.md)
- [Flare AI Skills guide](../guides/use-flare-ai-skills.md)
