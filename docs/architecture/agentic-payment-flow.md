# Architecture: Agentic Payment Flow

## x402 payment flow

```
XMTP Agent                    ProofRails API           Base (blockchain)
    │                               │                        │
    │── verify <bundle_url> ──────→ │                        │
    │                               │                        │
    │ ←── 402 { accepted: [         │                        │
    │      { amount: 0.001,         │                        │
    │        currency: USDC,        │                        │
    │        recipient: 0x... } ] } │                        │
    │                               │                        │
    │── USDC transfer ─────────────────────────────────────→ │
    │ ←── tx confirmed ────────────────────────────────────── │
    │                               │                        │
    │── POST /v1/x402/premium/      │                        │
    │   verify-bundle               │                        │
    │   X-PAYMENT: { tx_hash, ... } │                        │
    │                               │── query Base RPC ────→ │
    │                               │ ←── tx data ─────────── │
    │                               │── validate USDC transfer│
    │                               │── record payment        │
    │                               │── run verify logic      │
    │ ←── 200 { result... } ─────── │                        │
    │                               │                        │
    │   (if anchor_on_payment)      │                        │
    │                               │── BackgroundTask ──────→ Flare
    │                               │   anchor_bundle(hash)   │
```

## Agent anchoring flow

```
XMTP Agent                    ProofRails API           Flare (blockchain)
    │                               │                        │
    │── anchor {"key":"val"} ──────→ │                        │
    │   POST /anchor-data            │                        │
    │   { data, submit_onchain:true} │                        │
    │                               │── canonical_json()      │
    │                               │── sha256() → hash       │
    │                               │── INSERT AgentAnchor    │
    │                               │── BackgroundTask:       │
    │ ←── 200 {                     │   anchor_bundle(hash)──→ │
    │      anchor_hash: "0x...",    │                        │
    │      status: "pending" }      │ ←── txid ─────────────── │
    │                               │── UPDATE status:        │
    │                               │   confirmed             │
    │                               │   anchor_txid set       │
```

## Error propagation

The agent is designed to give users meaningful error messages:

| Backend status | Agent message |
|---------------|--------------|
| 402 | "This command requires a micropayment. Sending..." |
| 400 (bad X-PAYMENT) | "Payment header was malformed. Check wallet and USDC balance." |
| 403 | "Payment rejected — check recipient address and amount." |
| 401 | "Not authenticated. Check API key." |
| 503 | "Backend unavailable. Try again in a moment." |
| 5xx | "Backend error: \<detail\>" |

## State in the agent

The XMTP agent is stateless between messages. It does not cache receipts, payment history, or anchor records locally. All queries go to the ProofRails API.
