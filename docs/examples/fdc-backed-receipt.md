# Example: FDC-Backed Receipt (Proposed)

This example describes a **proposed** flow using the Flare Data Connector (FDC) to independently verify an XRPL payment before generating a ProofRails receipt.

**Status: Not yet implemented.** This documents the intended design for a future integration.

## Problem

When generating a receipt for an XRPL payment, ProofRails currently relies on the caller to provide the correct tx hash. A malicious or mistaken caller could submit a fake hash.

FDC solves this by requiring on-chain attestations from independent providers before accepting the data.

## Proposed flow

```
Client                        ProofRails           FDC Attestation Layer
   │                              │                        │
   │── POST /v1/receipts ─────→  │                        │
   │   { xrpl_txid: "...",       │                        │
   │     use_fdc: true }         │                        │
   │                             │── request attestation  │
   │                             │   for XRPL txid ──────→│
   │                             │                        │── providers query
   │                             │                        │   XRPL ledger
   │ ←── 202 Accepted ────────── │                        │
   │     { receipt_id: "...",    │                        │
   │       status: "awaiting_   │                        │
   │               attestation" }│                        │
   │                             │ ←── Merkle proof ──────│
   │                             │   (after threshold     │
   │                             │    providers agree)    │
   │                             │── verify proof on Flare│
   │                             │── generate ISO XML     │
   │                             │── anchor bundle hash   │
   │ ←── webhook: receipt.       │                        │
   │     anchored ─────────────→ │                        │
```

## What FDC provides

- **Independence**: attestation providers are separate from ProofRails.
- **Verifiability**: the Merkle proof can be verified by any Flare contract.
- **XRPL support**: FDC supports XRP Ledger payment attestations natively.

## Use Flare AI Skills to design this

```
Use flare-fdc to help me add FDC attestation verification to the ProofRails receipt 
creation flow. I need to:
1. Request an attestation for an XRPL payment txid
2. Wait for attestation threshold
3. Verify the Merkle proof
4. Extract the payment amount, sender, and receiver from the verified data
5. Use that verified data to generate the ISO 20022 message

Show me the contract interfaces and the API calls needed.
```

## See also

- [Flare-Native Implementations](../concepts/flare-native-implementations.md)
- [Flare AI Skills guide](../guides/use-flare-ai-skills.md)
- [Architecture: Flare Implementation](../architecture/flare-implementation.md)
