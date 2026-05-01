# What is ProofRails

ProofRails is an open translation and evidence layer for on-chain payments.

It sits between a blockchain and the systems that need to understand, report, or audit what happened. It does three things:

1. **Translates** on-chain payment data into ISO 20022-style records so existing financial infrastructure can consume it.
2. **Packages** those records into audit-grade evidence bundles — a ZIP archive containing the ISO XML, chain metadata, and a verifiable hash.
3. **Anchors** the bundle hash on-chain so any party can independently verify that a specific bundle existed at a specific point in time without trusting ProofRails itself.

## Why ISO 20022

ISO 20022 is the dominant messaging standard for inter-bank payments. It defines pain.001 (credit transfer initiation), pacs.008 (credit transfer settlement), camt.053 (account statement), and others. Moving to ISO 20022 is mandatory for most major payment corridors by 2025.

On-chain payments are not ISO 20022 — they are EVM transactions, UTXO transfers, or state channel closes. ProofRails bridges the gap by generating the relevant ISO messages for each transaction and producing evidence that those messages faithfully represent what happened on-chain.

## What ProofRails is not

- It is not a payment processor. It does not move money.
- It is not a wallet or exchange.
- It is not a compliance system — it provides evidence, not legal opinions.
- It is not a replacement for traditional banking rails.

## Actors

- **Platform operator**: runs the ProofRails middleware server and optionally the frontend.
- **Project owner**: registers a project, receives an API key, creates receipts for their on-chain activity.
- **Agent**: an AI or XMTP agent that uses x402 micropayments to access premium APIs and generates evidence for those payments.
- **Verifier**: any third party that downloads a bundle and independently confirms the hash matches the on-chain anchor.

## See also

- [ISO 20022 for On-Chain Payments](./iso-20022-for-onchain-payments.md)
- [Evidence Bundles](./evidence-bundles.md)
- [x402 Payments](./x402-payments.md)
- [Agentic Workflows](./agentic-workflows.md)
- [Flare-Native Implementations](./flare-native-implementations.md)
