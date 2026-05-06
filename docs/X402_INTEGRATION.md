# x402 Integration Guide

This middleware supports three x402-compatible payment paths. All premium endpoints return a `402 Payment Required` response listing every enabled option; clients and agents choose one.

---

## Payment Paths

### 1. USDC on Base (`erc20_transfer`)

| Field | Value |
|---|---|
| Network | Base mainnet (chainId 8453) |
| Asset | USDC |
| Token | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Mechanism | ERC-20 Transfer event on-chain |
| Default amount | `0.001` USDC |
| Env toggle | `X402_ENABLE_BASE_USDC=true` |

**X-PAYMENT header:**
```json
{
  "chain": "base",
  "chain_id": 8453,
  "currency": "USDC",
  "payment_type": "erc20_transfer",
  "tx_hash": "0xYourTransferTxHash",
  "amount": "0.001",
  "recipient": "0xRecipient"
}
```

---

### 2. USDT0 on Flare via X402Facilitator (`eip3009_facilitator`)

| Field | Value |
|---|---|
| Network | Flare mainnet (chainId 14) |
| Asset | USDT0 |
| Token | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |
| Mechanism | EIP-3009 `transferWithAuthorization` via X402Facilitator |
| Default amount | `0.001` USDT0 |
| Env toggle | `X402_ENABLE_FLARE_USDT0=true` |

#### How EIP-3009 settlement works

The payer signs a gasless off-chain authorization (EIP-3009 `transferWithAuthorization`). The authorization is then submitted to the `X402Facilitator` smart contract on Flare, which:
1. Verifies the signature is not expired and not replayed
2. Writes a `PaymentRecord` to contract storage (CEI pattern, before token call)
3. Calls `USDT0.transferWithAuthorization(from, to, value, ...)` — moving funds directly from payer to recipient
4. Emits `X402PaymentSettled(token, payer, recipient, amount, nonce, paymentId)`

The `X402Facilitator` never holds funds. Tokens flow payer → recipient in a single step.

#### Settlement modes

**Client-settled (default, `X402_SETTLEMENT_MODE=client`):**
The client submits the EIP-3009 authorization to the facilitator contract themselves, then provides the resulting transaction hash:

```json
{
  "chain": "flare",
  "chain_id": 14,
  "currency": "USDT0",
  "payment_type": "eip3009_facilitator",
  "token": "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
  "facilitator": "0xYourFacilitatorAddress",
  "recipient": "0xRecipient",
  "amount": "0.001",
  "settlement_tx_hash": "0xFacilitatorSettlementTxHash"
}
```

**Server-settled (`X402_SETTLEMENT_MODE=server`):**
The client provides the raw EIP-3009 signature fields. The API server submits the authorization to the facilitator using `X402_SETTLER_PRIVATE_KEY`:

```json
{
  "chain": "flare",
  "chain_id": 14,
  "currency": "USDT0",
  "payment_type": "eip3009_facilitator",
  "token": "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
  "facilitator": "0xYourFacilitatorAddress",
  "from": "0xPayer",
  "to": "0xRecipient",
  "value": "1000",
  "valid_after": "0",
  "valid_before": "1760000000",
  "nonce": "0xRandomBytes32",
  "v": 27,
  "r": "0x...",
  "s": "0x...",
  "authorization_type": "transferWithAuthorization"
}
```

> **Note:** `receiveWithAuthorization` is intentionally not used. EIP-3009 requires `msg.sender == to` for `receiveWithAuthorization`, which cannot be satisfied when a contract (the facilitator) is the caller. `transferWithAuthorization` is used for both settlement paths; the facilitator enforces `msg.sender == payload.to` as a guard on `settlePaymentAsPayee`.

---

### 3. Native FLR on Flare (`native_transfer`)

| Field | Value |
|---|---|
| Network | Flare mainnet (chainId 14) |
| Asset | FLR (native) |
| Mechanism | Native value transfer — verified against tx.value on-chain |
| Default amount | `0.05` FLR |
| Env toggle | `X402_ENABLE_FLARE_NATIVE_FLR=true` |

**X-PAYMENT header:**
```json
{
  "chain": "flare",
  "chain_id": 14,
  "currency": "FLR",
  "payment_type": "native_transfer",
  "tx_hash": "0xYourFLRTransferTxHash",
  "from": "0xPayer",
  "to": "0xRecipient",
  "amount": "0.05"
}
```

---

## 402 Response Format

Calling a premium endpoint without a valid `X-PAYMENT` header returns:

```http
HTTP/1.1 402 Payment Required
X-Payment-Required: true
Content-Type: application/json
```

```json
{
  "version": "1.0",
  "error": "payment_required",
  "endpoint": "premium_verify_bundle",
  "accepts": [
    {
      "scheme": "exact",
      "network": "base",
      "asset": "USDC",
      "payment_type": "erc20_transfer",
      "token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "chain_id": 8453,
      "decimals": 6,
      "recipient": "0xRecipient",
      "amount": "0.001"
    },
    {
      "scheme": "exact",
      "network": "flare",
      "asset": "USDT0",
      "payment_type": "eip3009_facilitator",
      "token": "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
      "facilitator": "0xFacilitator",
      "chain_id": 14,
      "decimals": 6,
      "recipient": "0xRecipient",
      "amount": "0.001"
    },
    {
      "scheme": "exact",
      "network": "flare",
      "asset": "FLR",
      "payment_type": "native_transfer",
      "chain_id": 14,
      "decimals": 18,
      "recipient": "0xRecipient",
      "amount": "0.05"
    }
  ]
}
```

---

## Premium Endpoints

| Endpoint | Method | Price | Description |
|---|---|---|---|
| `/v1/x402/premium/fx-lookup` | POST | 0.001 | FX rate lookup |
| `/v1/x402/premium/verify-bundle` | POST | 0.001 | Verify evidence bundle |
| `/v1/x402/premium/iso-message/{id}/{type}` | GET | 0.002 | Get ISO message artifact |
| `/v1/x402/premium/generate-statement` | POST | 0.005 | Generate camt.052/053 statement |
| `/v1/x402/premium/refund` | POST | 0.003 | Initiate refund via agent |
| `/v1/x402/premium/bulk-verify` | POST | 0.010 | Bulk verify up to 10 bundles |

Prices are in USDC (Base) or USDT0 (Flare). FLR prices are set separately via `X402_FLR_AMOUNT`.

---

## X402Facilitator Contract

**Source:** `contracts/X402Facilitator.sol`  
**Tests:** `contracts/test/X402Facilitator.test.js` (31 tests, Hardhat/Chai)  
**Deploy script:** `scripts/deploy_x402_facilitator.js`  
**Security audit:** `docs/security/X402Facilitator-audit.md`

### Key properties

- **CEI pattern** — all state writes happen before the external token call; safe against reentrancy even without the guard, but `nonReentrant` is applied regardless
- **No funds held** — tokens flow directly from payer to recipient via `transferWithAuthorization`; the contract balance is always zero after settlement
- **Dual settlement paths** — `settlePaymentAsPayee` (restricted to `msg.sender == recipient`) and `settlePayment` (callable by anyone with the authorization)
- **Idempotency** — payments keyed by `keccak256(from, to, token, value, nonce)`; duplicate submissions revert with `PaymentAlreadySettled`
- **Nonce replay protection** — EIP-3009 `authorizationState` checked before settlement
- **Per-token minimums** — `setMinimumAmount(token, amount)` configurable by owner; fallback `DEFAULT_MIN = 1` prevents zero-value spam
- **Pausable** — owner can call `pause()` to halt all settlements in an emergency
- **Ownable** — owner controls token allowlist, minimum amounts, and pause

### Settlement flow

```
Client                      X402Facilitator              USDT0 token
  │                               │                          │
  │  settlePaymentAsPayee(payload)│                          │
  │──────────────────────────────►│                          │
  │                               │ checks: token supported  │
  │                               │ checks: not expired      │
  │                               │ checks: amount >= min    │
  │                               │ checks: not settled      │
  │                               │ checks: nonce unused     │
  │                               │ writes: payments[id]     │ ← Effects before Interaction
  │                               │ emits: X402PaymentSettled│
  │                               │                          │
  │                               │ transferWithAuthorization│
  │                               │─────────────────────────►│
  │                               │                          │ moves tokens payer→recipient
  │◄──────────────────────────────│                          │
  │  returns: paymentId           │                          │
```

### Deployment

See `DEPLOY.md` Step 1 for full instructions. Quick reference:

```bash
# Compile
npx hardhat compile

# Deploy to Coston2 testnet
DEPLOYER_PRIVATE_KEY=0x... X402_RECIPIENT_ADDRESS=0x... \
  node scripts/deploy_x402_facilitator.js --network coston2

# Deploy to Flare mainnet
DEPLOYER_PRIVATE_KEY=0x... X402_RECIPIENT_ADDRESS=0x... \
  node scripts/deploy_x402_facilitator.js --network flare
```

---

## Analytics Endpoints

These endpoints are available for monitoring and revenue tracking (authentication required).

### List payments

```http
GET /v1/x402/payments?currency=USDT0&chain=flare&status=verified&limit=50&offset=0
```

Filters: `currency`, `chain`, `status`, `payment_type`

### Revenue summary

```http
GET /v1/x402/revenue?days=7
```

Returns total revenue, payment count, breakdown by currency/chain, breakdown by payment_type, and per-endpoint stats.

### Facilitator config (admin)

```http
GET /v1/x402/facilitator-config
```

Returns the full current x402 configuration as read from environment settings.

---

## Error Reference

| HTTP | `detail` | Meaning |
|---|---|---|
| 402 | — | No payment provided |
| 400 | `invalid_payment_header` | Malformed JSON in X-PAYMENT |
| 400 | `unsupported_payment_type:<type>` | Unknown `payment_type` |
| 400 | `usdt0_payment_not_enabled` | `X402_ENABLE_FLARE_USDT0=false` |
| 400 | `wrong_token_address` | Token in header ≠ `X402_USDT0_FLARE_ADDRESS` |
| 400 | `wrong_facilitator_address` | Facilitator in header ≠ `X402_FLARE_FACILITATOR_ADDRESS` |
| 400 | `facilitator_not_configured` | `X402_FLARE_FACILITATOR_ADDRESS` env var not set |
| 403 | `payment_verification_failed:transaction_not_found` | TX not found on chain |
| 403 | `payment_verification_failed:token_mismatch` | Wrong token in event log |
| 403 | `payment_verification_failed:wrong_recipient` | Wrong recipient in event |
| 403 | `payment_verification_failed:insufficient_amount` | Amount below required |
| 403 | `payment_verification_failed:wrong_facilitator` | TX sent to wrong contract |
| 403 | `payment_verification_failed:transaction_reverted` | TX failed on-chain |
| 409 | `payment_already_used` | TX hash already recorded in DB |
| 409 | `nonce_already_used` | EIP-3009 nonce already recorded in DB |

---

## Environment Variables Reference

```bash
# --- Shared ---
X402_RECIPIENT_ADDRESS=0x...        # fallback recipient for all paths

# --- Feature toggles ---
X402_ENABLE_BASE_USDC=true
X402_ENABLE_FLARE_USDT0=true
X402_ENABLE_FLARE_NATIVE_FLR=true

# --- Base USDC ---
X402_BASE_RPC_URL=https://mainnet.base.org
X402_USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
X402_USDC_AMOUNT=0.001
X402_BASE_RECIPIENT=0x...           # overrides X402_RECIPIENT_ADDRESS for USDC

# --- Flare USDT0 ---
X402_FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
X402_FLARE_CHAIN_ID=14
X402_USDT0_FLARE_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D
X402_USDT0_DECIMALS=6
X402_USDT0_AMOUNT=0.001
X402_FLARE_FACILITATOR_ADDRESS=0x... # deployed X402Facilitator contract address
X402_USDT0_RECIPIENT=0x...           # overrides X402_RECIPIENT_ADDRESS for USDT0
X402_FLARE_CONFIRMATIONS=1

# --- Flare FLR ---
X402_FLR_AMOUNT=0.05
X402_FLR_RECIPIENT=0x...             # overrides X402_RECIPIENT_ADDRESS for FLR

# --- Settlement mode ---
X402_SETTLEMENT_MODE=client          # "client" or "server"
X402_SETTLER_PRIVATE_KEY=            # only needed when mode=server
```

---

## Security Notes

- All token amounts use Python `Decimal` internally — no floating-point rounding errors
- `eip3009_nonce` is unique-indexed per `(nonce, chain_id, token_address)` in the database — database-level replay protection independent of the contract
- `tx_hash` is unique-indexed in the database — prevents reuse of a settlement transaction across different API calls
- The X402Facilitator contract provides on-chain replay protection via EIP-3009 `authorizationState`
- `transferWithAuthorization` is used (not `receiveWithAuthorization`) because `receiveWithAuthorization` requires `msg.sender == to`, which cannot be satisfied when a contract calls it — the facilitator contract would be `msg.sender`, not the recipient
- FXRP is **not** supported (it lacks EIP-3009)

---

## See Also

- [`DEPLOY.md`](../DEPLOY.md) — full deployment guide including contract deployment
- [`docs/security/X402Facilitator-audit.md`](security/X402Facilitator-audit.md) — internal security audit report
- [`contracts/X402Facilitator.sol`](../contracts/X402Facilitator.sol) — contract source
- [`docs/FLARE_INTEGRATION.md`](FLARE_INTEGRATION.md) — Flare-specific RPC and network setup
