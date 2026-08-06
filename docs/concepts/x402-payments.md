# x402 Payment Paths in ProofRails

ProofRails implements three x402-compatible payment paths. Clients and autonomous agents pick one based on their chain preference and tooling.

x402 refers to HTTP 402 Payment Required — a status code defined in 1996 and left unused until on-chain micropayments made it practical. A protected endpoint returns `402` with an `accepts` array of payment options; the client pays on-chain and retries with an `X-PAYMENT` header.

---

## 1. USDC on Base (`erc20_transfer`)

The simplest path. The client sends USDC to a recipient wallet on Base network and provides the transfer transaction hash.

| Field | Value |
|---|---|
| Chain | Base (chainId 8453) |
| Token | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Mechanism | ERC-20 Transfer event verification |
| EIP-3009 | No |
| Server key required | No |

**Flow:** client sends USDC → ProofRails queries Base for the `Transfer` event → endpoint unlocked.

---

## 2. USDT0 on Flare via EIP-3009 Facilitator (`eip3009_facilitator`)

The canonical Flare-native x402-compatible path. USDT0 is the OFT-bridged version of USDT deployed on Flare mainnet by Tether/LayerZero. It supports EIP-3009 (`transferWithAuthorization` / `receiveWithAuthorization`), enabling gasless, off-chain-signed authorizations that an `X402Facilitator` contract can atomically settle.

| Field | Value |
|---|---|
| Chain | Flare mainnet (chainId 14) |
| Token | USDT0 `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |
| Mechanism | EIP-3009 + `X402Facilitator` contract |
| EIP-3009 signed type | **`TransferWithAuthorization`** |
| Settlement function | **`settlePayment()`** (payer-callable) |
| Server key required | Only in server-settlement mode |
| Audit status | Facilitator unaudited; built on audited OpenZeppelin primitives |

**Flow (client-settled — default):**
1. Client signs an EIP-3009 **`TransferWithAuthorization`** payload off-chain (no gas). The facilitator calls `USDT0.transferWithAuthorization()` internally, so the signed EIP-712 type must be `TransferWithAuthorization` — signing `ReceiveWithAuthorization` produces a different typehash and the signature is rejected on-chain.
2. Client calls `X402Facilitator.settlePayment(payload)`. This function is callable by anyone, including the payer.
3. Client provides the `settlement_tx_hash` in the `X-PAYMENT` header.
4. ProofRails verifies the `X402PaymentSettled` event (token, recipient, amount) and unlocks the endpoint.

**Flow (server-settled):**
1. Client signs the `TransferWithAuthorization` payload off-chain.
2. Client provides the full authorization fields (`from`, `to`, `value`, `validAfter`, `validBefore`, `nonce`, `v`, `r`, `s`) in `X-PAYMENT`.
3. ProofRails submits the authorization to the facilitator via its own wallet (`X402_SETTLER_PRIVATE_KEY`).
4. ProofRails verifies the event and unlocks the endpoint.

### Why `settlePayment()` and not `settlePaymentAsPayee()`?

Autonomous agents are **payers**, not recipients. `settlePaymentAsPayee()` requires `msg.sender == payload.to` (the recipient), so a payer cannot call it. `settlePayment()` is callable by anyone — including the payer — and is the correct entry point for client-settled mode. `settlePaymentAsPayee()` is reserved for the recipient (server-settled mode where ProofRails is the payee).

The EIP-712 domain `name` must be read from the token contract at runtime (`name()` returns `"USD₮0"`) — do not hardcode it, or the domain separator will mismatch.

---

## 3. Native FLR Transfer (`native_transfer`)

A simpler HTTP 402 payment gate using the Flare native token. No EIP-3009 is involved — just a standard Flare native transfer.

| Field | Value |
|---|---|
| Chain | Flare mainnet (chainId 14) |
| Token | FLR (native) |
| Mechanism | Native transfer value verification |
| EIP-3009 | No |
| Server key required | No |

**Flow:** client sends FLR to recipient → ProofRails queries Flare for the transaction value → endpoint unlocked.

Note: this path is HTTP 402 payment-gating, not the EIP-3009 authorization pattern used by the canonical x402 protocol.

---

## Protocol flow

```
Client                          ProofRails (server)
  |                                     |
  |-- POST /v1/x402/premium/fx-lookup ->|
  |                                     |-- (no X-PAYMENT header)
  |<-- 402 Payment Required ------------|
  |    { "version": "1.0",              |
  |      "error": "payment_required",   |
  |      "accepts": [                   |
  |        { "payment_type":            |
  |            "erc20_transfer", ... },  |
  |        { "payment_type":            |
  |            "eip3009_facilitator",.. }|
  |        { "payment_type":            |
  |            "native_transfer", ... }  |
  |      ] }                            |
  |                                     |
  |-- (client pays on chosen chain) -> Blockchain
  |<-- tx confirmed -------------------|
  |                                     |
  |-- POST /v1/x402/premium/fx-lookup ->|
  |    X-PAYMENT: { payment_type, ... } |
  |                                     |-- verify on correct chain/path
  |                                     |-- reject replayed tx
  |                                     |-- record payment
  |<-- 200 { result... } ---------------|
```

## Payment verification

In production mode, the middleware:

1. Parses the `X-PAYMENT` header as JSON (malformed → `400`).
2. Routes by `payment_type`: `eip3009_facilitator` / `native_transfer` → `FlarePaymentVerifier`; `erc20_transfer` → Base USDC verifier.
3. For USDT0: validates the declared token and facilitator against config (`400 wrong_token_address` / `wrong_facilitator_address`), then verifies the `X402PaymentSettled` event.
4. Confirms correct recipient, amount, and confirmation depth (`403` on failure).
5. Rejects reused settlement/transfer tx hashes (`409 payment_already_used`).
6. Records the payment in `x402_payments`.

In development mode (`X402_MOCK_PAYMENTS=true`), on-chain verification is skipped. This is for local development and tests only — never set in production.

## Premium endpoints

| Endpoint | USDC price | FLR price | Function |
|----------|-----------|-----------|---------|
| `POST /v1/x402/premium/verify-bundle` | 0.001 | 0.05 | Verify an evidence bundle |
| `POST /v1/x402/premium/generate-statement` | 0.005 | 0.25 | Generate a camt.052/053 statement |
| `POST /v1/x402/premium/fx-lookup` | 0.001 | 0.05 | Current FX rate (FTSO) |
| `POST /v1/x402/premium/bulk-verify` | 0.010 | 0.50 | Verify multiple bundles |
| `POST /v1/x402/premium/refund` | 0.003 | 0.15 | Initiate a refund |

FLR prices are configurable via env vars (`X402_FLR_VERIFY`, `X402_FLR_STATEMENT`, etc.). Current pricing: `GET /v1/x402/pricing`. Live facilitator/path config: `GET /v1/x402/facilitator-config` (admin).

## Environment variables

```env
X402_RECIPIENT_ADDRESS=0x...        # shared fallback recipient
X402_BASE_RECIPIENT=0x...           # USDC recipient on Base (falls back to shared)
X402_USDT0_RECIPIENT=0x...          # USDT0 recipient on Flare (falls back to shared)
X402_FLR_RECIPIENT=0x...            # FLR recipient on Flare (falls back to shared)
X402_FLARE_FACILITATOR_ADDRESS=0x...# X402Facilitator contract on Flare
X402_ENABLE_BASE_USDC=true          # toggle the USDC path in 402 options
X402_ENABLE_FLARE_USDT0=true        # toggle the USDT0 path
X402_ENABLE_FLARE_NATIVE_FLR=true   # toggle the native-FLR path
X402_SETTLEMENT_MODE=client         # client | server
X402_SETTLER_PRIVATE_KEY=0x...      # server-settled mode only
X402_MOCK_PAYMENTS=true             # DEV ONLY — skip on-chain verification
```

## FXRP status

FXRP does not currently support EIP-3009 — the required `transferWithAuthorization` method is not available on the FXRP token contract. FXRP x402 support is future work, contingent on FXRP gaining EIP-3009 or an equivalent authorization path.

## Correct public language

> ProofRails supports an x402-compatible payment path using USDT0 on Flare via EIP-3009 facilitator settlement, plus native FLR transfer as a separate HTTP 402 payment gate, plus USDC on Base. FXRP x402 is not yet supported because FXRP does not implement EIP-3009.

Do not say "Official x402 is live on Flare" unless formally verified by the x402 upstream. Do not say "FXRP x402 is live."

## Analytics

- `GET /v1/x402/payments` — list verified payments (auth required)
- `GET /v1/x402/revenue?days=7` — revenue summary (admin only)

## See also

- [Use x402 Paid Endpoints](../guides/use-x402-paid-endpoints.md)
- [API: x402](../api/x402.md)
- [Agentic Workflows](./agentic-workflows.md)
