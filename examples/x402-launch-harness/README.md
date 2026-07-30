# x402 launch harness

Deterministic CLI used to record one complete ProofRails journey on Flare mainnet:
HTTP 402 → official x402 payment → same-endpoint 200 → receipt → signed evidence
bundle → Flare anchor → independent verification.

It calls the live protected endpoint `POST https://app.proofrails.com/v1/x402/premium/fx-lookup`
with body `{"base_ccy":"USD","quote_ccy":"FLR"}` using the official client versions
pinned by the verified ProofRails example.

## Dependency versions

| Package       | Version                  |
| ------------- | ------------------------ |
| `@x402/fetch` | 2.19.0                   |
| `@x402/evm`   | 2.19.0                   |
| `viem`        | 2.37.6                   |
| Node.js       | ≥ 20 (tested on 20.18.1) |

```bash
cd examples/x402-launch-harness
npm ci
```

## Modes

### `preflight` — read-only, never signs

```bash
node harness.mjs preflight
```

Fetches the 402 challenge, decodes `PAYMENT-REQUIRED` and asserts the exact tuple
(network `eip155:14`, USD₮0 `0xe7cd…C82D`, `1000` raw units, recipient
`0x0A61…0ef4`, facilitator `0xa78F…A4aE`, EIP-712 domain), then reads Flare
mainnet directly: chain ID, bytecode presence for token/facilitator/EvidenceAnchor,
`paused()`, `supportedTokens()`, `minimumAmounts()`, payer USD₮0 and FLR balances,
freshness of a candidate authorization nonce on both the facilitator and the token,
gas price with a conservative fee estimate and a hard fee ceiling.

No signature is created and no transaction is broadcast. Exit code is non-zero
unless every check passes. The full tuple is written to `runs/preflight-<ts>.json`.

`PAYER_ADDRESS` alone is enough for preflight; the private key is not needed.

### `record` — exactly one approved payment

```bash
PAYER_PRIVATE_KEY=... APPROVED_PAYMENT_ID="<approval reference>" node harness.mjs record
```

Guards, in order:

1. `PAYER_PRIVATE_KEY` must be present.
2. `APPROVED_PAYMENT_ID` must be present — an unattended run cannot spend value.
3. `runs/broadcast.lock` must not exist; it is written immediately before the paid
   request and never removed by the harness, so a second payment cannot happen.
4. A clean `preflight` must pass in the same process.

The paid request goes through `wrapFetchWithPaymentFromConfig` with
`ExactEvmScheme`, so the authorization is signed locally and settled by the
ProofRails facilitator. Failures are never retried. The harness then prints the
delivered result, decodes `PAYMENT-RESPONSE`, polls the receipt through its real
lifecycle states and runs `verify` once the receipt is anchored.

### `verify` — independent integrity check

```bash
node harness.mjs verify <receipt_id> [--run=runs/run-<receipt_id>.json] [--settlement-tx=0x…]
```

Downloads the current `evidence.zip`, recomputes its SHA-256, recomputes every
`manifest.json` file hash and size, verifies `manifest.sig` as Ed25519 against
`public_key.pem`, compares the delivery/resource hash with the delivered bytes,
decodes `X402PaymentSettled` from the settlement transaction, decodes
`EvidenceAnchored` from the receipt's `flare_txid` and compares the committed
bundle hash with the current served bundle hash.

The PASS table is derived from these checks; nothing in it is hardcoded. Results
are written to `runs/verification-<receipt_id>.json`.

## Safety notes

- `record` spends real USD₮0 on Flare mainnet and creates an irreversible
  settlement transaction. Wallet funding is not approval.
- A duplicate authorization nonce is rejected with HTTP 409 `nonce_already_used`.
  Do not create a second payment because receipt processing or anchoring is
  still pending.
- An onchain anchor proves integrity and timing of the committed hash, not the
  truth or legal sufficiency of offchain data.

ProofRails operates an integrated x402 facilitator for its own payment-gated APIs;
on Flare, USDT0 settlement uses the ProofRails X402Facilitator contract.
