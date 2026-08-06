# Implementation Plan: Flare USDT0 x402

**Status:** Implemented  
**Date:** 2026-05-05

---

## Architecture

Three payment paths, all exposed via the same `require_payment` decorator:

```
X-PAYMENT header present?
  No  → 402 with all enabled payment options
  Yes → detect payment_type
         eip3009_facilitator → FlarePaymentVerifier.verify_usdt0_settlement_tx()
         native_transfer     → FlarePaymentVerifier.verify_flr_transfer()
         erc20_transfer      → X402PaymentVerifier.verify_payment()
```

## Files Changed

| File | Change |
|---|---|
| `app/settings.py` | Added x402 Flare env vars |
| `app/models.py` | Extended X402Payment with payment_type, token_address, etc. |
| `app/x402.py` | Rewrote to support multi-path; 402 response includes all enabled options |
| `app/x402_flare.py` | New — Flare USDT0 + FLR verification logic |
| `contracts/X402Facilitator.sol` | New — x402-compatible EIP-3009 facilitator |
| `scripts/deploy_x402_facilitator.js` | New — deployment script |
| `alembic/versions/f3a9d1c05e82_...py` | New — DB migration |
| `.env.example` | Added x402 Flare vars |
| `docs/research/flare-usdt0-x402-confirmation.md` | New — research report |
| `docs/concepts/x402-payments.md` | New — concept doc |
| `docs/FLARE_INTEGRATION.md` | New — Flare integration guide |
| `docs/guides/use-flare-usdt0-x402.md` | New — usage guide |
| `examples/flare-usdt0-x402-agent/` | New — TypeScript agent example |
| `tests/test_x402_usdt0_unit.py` | New — unit tests |

## DB Changes

Migration `f3a9d1c05e82` adds to `x402_payments`:
- `payment_type` (erc20_transfer | eip3009_facilitator | native_transfer)
- `raw_amount` (integer as string)
- `chain_id`
- `token_address`
- `facilitator_address`
- `payer_address`
- `eip3009_nonce` (for replay protection)
- `authorization_type`
- `facilitator_payment_id`
- `status` (pending | verified | failed)
- `tx_hash` made nullable (server-submitted mode)
- Partial unique index on `tx_hash` (non-NULL only)
- Unique index on `(eip3009_nonce, chain_id, token_address)`

## Settlement Modes

**client** (default): Client calls `X402Facilitator.settlePaymentAsPayee()` and sends `settlement_tx_hash`. Server verifies event only. No server private key needed.

**server**: Client sends raw EIP-3009 authorization fields. Server submits to facilitator via `X402_SETTLER_PRIVATE_KEY`. Higher ops burden; requires key management.

## Risks / Follow-ups

| Risk | Mitigation | Status |
|---|---|---|
| Facilitator unaudited | Labeled as such; built on OZ primitives | Known |
| Mainnet facilitator not deployed | Deployment script ready; address TBD | Blocked on deployment |
| FXRP not supported | Documented; FXRP lacks EIP-3009 | Future work |
| Server key management | Optional; documented risks | Documented |
| Flare RPC reliability | Standard retry via web3.py default | Acceptable |
