# Flare-Native Implementations

This document describes how ProofRails uses and can extend Flare Network's
infrastructure. Entries are tagged:

- **Implemented** — working in this branch
- **Prototype** — partial implementation, not production-complete
- **Proposed** — design exists, not implemented

---

## 1. Flare EVM — Evidence Hash Anchoring

**Status: Implemented**

ProofRails anchors the SHA-256 hash of each evidence bundle to the Flare C-Chain
using the `EvidenceAnchor` smart contract. This creates a tamper-proof timestamp that
any party can independently verify without accessing ProofRails infrastructure.

**How it works:**

1. The receipt pipeline generates an ISO 20022 XML and an evidence bundle (ZIP of
   XML + metadata).
2. `app/anchor.py` computes `sha256(zip_bytes)` and calls `anchor(bytes32 hash)` on the
   contract.
3. The resulting `flare_txid` is stored on the receipt and returned to callers.
4. Anyone can verify by calling `getAnchor(bytes32 hash)` on the same contract.

**Configuration:**

```env
FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ANCHOR_CONTRACT_ADDR=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
ANCHOR_PRIVATE_KEY=0x...
```

**Multi-chain support:** Projects can configure additional chains (Ethereum, Polygon,
Coston2) via `PUT /v1/projects/{id}/config`.

---

## 2. FTSO v2 — On-Chain FX Price Feeds

**Status: Implemented**

Flare's FTSO v2 oracle provides tamper-proof, block-level price feeds for 30+ trading
pairs. ProofRails uses FTSO to enrich ISO 20022 reports with exchange rates that are
cryptographically verifiable.

**Endpoints:**

- `GET /v1/flare/feeds` — all available feeds with current price, decimals, timestamp
- `GET /v1/flare/feeds/{symbol}` — single feed (e.g. `FLR%2FUSD`)
- `POST /v1/x402/premium/fx-lookup` — payment-gated FX lookup with FTSO as default provider

**Contract resolution:**

```python
registry = ContractRegistry(FTSO_REGISTRY_ADDRESS)
ftso = registry.getContractAddressByName("FtsoV2")
(value, decimals, timestamp) = ftso.getFeedById(bytes21(feed_id))
```

**Using the flare-ftso AI Skill:**

When building FTSO-aware features, ask Claude with the `flare-ftso` skill active:

```
Use flare-ftso to explain how to query FLR/USD price for an ISO 20022 FX conversion field.
```

**Configuration:**

```env
FTSO_ENABLED=true
FTSO_REGISTRY_ADDRESS=0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019
FTSO_CACHE_TTL=90   # seconds — FTSO updates every ~90s
```

---

## 3. Flare Data Connector (FDC) — Cross-Chain Payment Verification

**Status: Prototype**

FDC allows Flare smart contracts to verifiably access data from external blockchains
(Bitcoin, XRPL, Ethereum, etc.) via Merkle proofs attested by the validator set.

ProofRails uses FDC to verify that a payment actually occurred on an external chain
before generating an ISO 20022 receipt. This closes the trust gap: receipts are not
just self-reported — they are backed by cryptographic proof of the on-chain event.

**Current implementation (`POST /v1/flare/fdc/prepare-attestation`):**

Constructs the FDC verifier request body for a given transaction. Does NOT submit
to the DA layer or retrieve a proof. The response is the JSON you would POST to the
FDC verifier service.

**Full flow (proposed):**

```
1. Client provides tx_hash + chain
2. ProofRails calls FDC Verifier: POST /EVMTransaction/prepareRequest
3. FDC DA Layer processes the request over the next voting round (~90s)
4. ProofRails retrieves the Merkle proof: GET /EVMTransaction/proof/{requestId}
5. Receipt generation proceeds only if proof.status == "OK"
6. Proof root stored on receipt for downstream verification
```

**Using the flare-fdc AI Skill:**

```
Use flare-fdc to design the FDC attestation flow for verifying a Base chain USDC payment
before issuing a ProofRails receipt.
```

**Configuration:**

```env
FDC_VERIFIER_URL=https://fdc-verifiers-testnet.flare.network
FDC_DA_LAYER_URL=https://fdc-da-layer-testnet.flare.network
FDC_API_KEY=your_key
```

---

## 4. FAssets — Evidence for Wrapped Cross-Chain Assets

**Status: Proposed**

FAssets (FXRP, FBTC, FDOGE) are Flare-native representations of assets from
non-EVM chains. As FAssets transactions settle on Flare, they generate on-chain
events that ProofRails could index to automatically produce ISO 20022 receipts for
cross-chain transfers.

**Proposed flow:**

1. Index `FAssetMinted` / `FAssetRedeemed` events from the FAssets contract.
2. Map each event to a ProofRails receipt with ISO `pain.001` XML.
3. Anchor the receipt hash on Flare EVM.
4. Expose the receipt via the standard ProofRails API.

**Why it matters:** Banks and regulated entities receiving FXRP payments need an
ISO 20022 record of the underlying XRPL transfer. ProofRails can bridge the two
worlds without requiring the payment originator to interact with legacy banking
infrastructure.

**Using the flare-fassets AI Skill:**

```
Use flare-fassets to explain how FAsset minting events map to ISO 20022 payment
notification fields for a FXRP transfer.
```

---

## 5. Smart Accounts — XRPL-to-Flare User Flows

**Status: Proposed**

Flare Smart Accounts allow XRPL accounts to be linked to Flare EVM addresses via
cryptographic delegation. This enables XRPL-originating users to trigger Flare-side
operations (receipt generation, evidence anchoring) without owning an EVM wallet.

**Proposed flow:**

1. XRPL user delegates to a Flare EVM address using the Smart Accounts service.
2. ProofRails validates the delegation signature.
3. The XRPL address is recorded as `sender_wallet` in the receipt.
4. Evidence is anchored on Flare EVM using the delegated address.

**Using the flare-smart-accounts AI Skill:**

```
Use flare-smart-accounts to design the XRPL address delegation check before
creating a ProofRails receipt for an XRPL payment.
```

---

## 6. Flare AI Skills — Developer Tooling

**Status: Implemented (IDE configuration)**

The `.claude/settings.json` in this repo configures Claude Code to load five Flare
AI Skills as MCP servers:

| Skill | Purpose |
|---|---|
| `flare-general` | Chain IDs, RPCs, explorer links, contract addresses |
| `flare-ftso` | FTSO v2 feed IDs, query patterns, price aggregation |
| `flare-fdc` | FDC attestation types, request/proof flows |
| `flare-fassets` | FAssets minting/redemption, cross-chain bridge events |
| `flare-smart-accounts` | XRPL delegation, account linking, signature verification |

When developing ProofRails features that touch Flare infrastructure, these skills
provide accurate, protocol-specific guidance to the coding agent.

**Install prompt (Claude Code will offer this automatically):**

```
Install Flare AI Skills MCP servers for this project? [Y/n]
```

If not prompted, run:

```bash
claude mcp add flare-general -- npx -y @flare-foundation/flare-ai-skills flare-general
```

---

## Summary table

| Feature | Status | Endpoint / Hook | Flare Primitive |
|---|---|---|---|
| Evidence hash anchoring | ✅ Implemented | `jobs.py` → `anchor.py` | Flare EVM contract |
| FX rate enrichment | ✅ Implemented | `GET /v1/flare/feeds` | FTSO v2 |
| FDC request builder | 🔧 Prototype | `POST /v1/flare/fdc/prepare-attestation` | FDC Verifier |
| FDC full proof flow | 🔲 Proposed | — | FDC DA layer + on-chain verify |
| FAssets evidence | 🔲 Proposed | — | FAssets events |
| Smart Accounts flows | 🔲 Proposed | — | Smart Accounts delegation |
| AI Skills (IDE) | ✅ Implemented | `.claude/settings.json` | Flare AI Skills MCP |
