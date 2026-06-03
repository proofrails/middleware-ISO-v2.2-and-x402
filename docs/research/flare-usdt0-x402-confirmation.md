# Flare USDT0 x402 Confirmation Research

**Date:** 2026-05-05  
**Author:** ProofRails engineering  
**Status:** Confirmed — implementation proceeding

---

## 1. USDT0 Contract on Flare Mainnet

### Contract Address

| Field | Value |
|---|---|
| **Address** | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |
| **Token name** | USD₮0 |
| **Symbol** | USDT0 |
| **Decimals** | 6 |
| **Chain ID** | 14 (Flare mainnet) |
| **Explorer** | https://flarescan.com/address/0xe7cd86e13AC4309349F30B3435a9d337750fC82D |
| **Contract type** | TetherTokenOFTExtension (LayerZero OFT) |

### Sources of Truth

1. **Official USDT0 deployments page** — `docs.usdt0.to/technical-documentation/deployments` lists Flare mainnet Token: `0xe7cd86e13AC4309349F30B3435a9d337750fC82D`
2. **Flare DevHub gasless USDT0 guide** — `dev.flare.network/network/guides/gasless-usdt0-transfers` hardcodes the same address in its `.env` examples (`USD0_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D`)
3. **LayerZero Endpoint ID for Flare mainnet:** 30295

Additional deployment addresses from the USDT0 deployment registry:
- OFT (LayerZero adapter): `0x567287d2A9829215a37e3B88843d32f9221E7588`
- Safe (multisig): `0x6ae078461f35c3cC216A71029F71ee7Bc4d9a10b`

---

## 2. EIP-3009 Support

### Verdict: YES — Both `transferWithAuthorization` and `receiveWithAuthorization` are supported

### Evidence

#### a) Flare DevHub ABI

The official Flare DevHub repository (`flare-foundation/developer-hub`) ships `USD0.json` with the full ABI. The ABI exposes `transferWithAuthorization` with the canonical EIP-3009 signature:

```json
{
  "name": "transferWithAuthorization",
  "inputs": [
    {"name": "from",        "type": "address"},
    {"name": "to",          "type": "address"},
    {"name": "value",       "type": "uint256"},
    {"name": "validAfter",  "type": "uint256"},
    {"name": "validBefore", "type": "uint256"},
    {"name": "nonce",       "type": "bytes32"},
    {"name": "signature",   "type": "bytes"}
  ]
}
```

> Note: The ABI uses a packed `bytes signature` parameter. The on-chain `EIP3009.sol` implementation unpacks it internally. When calling directly via `ethers`, the v/r/s split form is also accepted via the overloaded function selector.

#### b) OpenZeppelin Audit of USDT0

OpenZeppelin audited the USDT0 codebase (audit report: `openzeppelin.com/news/usdt0-audit`). The audit confirms:

- `TetherTokenOFTExtension` and `ArbitrumExtensionV2` both inherit `EIP3009.sol`
- `transferWithAuthorization` and `receiveWithAuthorization` are implemented
- `receiveWithAuthorization` carries an `onlyNotBlocked` modifier (caller must be the `to` address)

#### c) Flare DevHub Gasless USDT0 Guide

The guide at `dev.flare.network/network/guides/gasless-usdt0-transfers` explicitly calls `usd0.transferWithAuthorization(from, to, value, validAfter, validBefore, nonce, v, r, s)` against the confirmed mainnet address.

### Required Methods

| Method | Available | Notes |
|---|---|---|
| `transferWithAuthorization` | ✅ | Standard EIP-3009 |
| `receiveWithAuthorization` | ✅ | Caller must be `to`, front-running protected |
| `authorizationState(address, bytes32)` | ✅ | Returns bool for nonce state |
| `DOMAIN_SEPARATOR()` | ✅ | EIP-712 domain separator |
| `nonces(address)` | N/A | Not EIP-2612 style; uses EIP-3009 bytes32 nonces |
| `name()` | ✅ | Returns "USD₮0" |
| `version()` (EIP-712) | ✅ | "1" |

### Security Consideration: `receiveWithAuthorization` vs `transferWithAuthorization`

`receiveWithAuthorization` requires `msg.sender == payload.to` — only the recipient (or a contract they call) can execute it. This eliminates front-running risk: a malicious MEV bot cannot intercept a signed authorization and redirect the payment.

`transferWithAuthorization` can be called by anyone who has the signature, introducing front-running risk in adversarial environments.

**Decision:** The ProofRails facilitator uses `settlePaymentAsPayee` (calling `receiveWithAuthorization`) as the primary settlement path. `transferWithAuthorization` is supported as fallback.

---

## 3. EIP-712 Domain

### Domain Parameters

| Field | Value |
|---|---|
| `name` | Read via `token.name()` at signing time → `"USD₮0"` |
| `version` | `"1"` |
| `chainId` | `14` |
| `verifyingContract` | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |

> **Do not hardcode the name.** The Flare DevHub explicitly fetches `tokenName = await tokenContract.name()` at signing time to ensure domain separator accuracy.

### TypeScript Signing Example

```typescript
const domain = {
  name: await usdt0.name(),  // "USD₮0"
  version: "1",
  chainId: 14n,
  verifyingContract: "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
};

const types = {
  TransferWithAuthorization: [
    { name: "from",        type: "address" },
    { name: "to",          type: "address" },
    { name: "value",       type: "uint256" },
    { name: "validAfter",  type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce",       type: "bytes32" },
  ],
};

// Or for receiveWithAuthorization:
const types2 = {
  ReceiveWithAuthorization: [
    { name: "from",        type: "address" },
    { name: "to",          type: "address" },
    { name: "value",       type: "uint256" },
    { name: "validAfter",  type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce",       type: "bytes32" },
  ],
};
```

---

## 4. Facilitator Contract Source

### Selected Source

**Flare foundation's `X402Facilitator.sol`** from `github.com/flare-foundation/flare-hardhat-starter/blob/main/contracts/x402/X402Facilitator.sol`

| Field | Value |
|---|---|
| License | MIT |
| Audit status | Based on OpenZeppelin patterns (Ownable, ReentrancyGuard). No standalone audit confirmed. Labeled as unaudited in our deployment. |
| OpenZeppelin deps | `@openzeppelin/contracts/access/Ownable.sol`, `@openzeppelin/contracts/utils/ReentrancyGuard.sol` |
| Deployed addresses | None pre-deployed on Flare mainnet — ProofRails will deploy its own instance |

### Modifications Required for ProofRails

The source is used near-verbatim with a minor modification:
- Added `X402PaymentSettled` event matching the required spec (the upstream `PaymentSettled` event was already emitted — name aligned)
- Added `requiredAmount` validation guard (minimum acceptable payment amount per token)
- No other structural changes

### Coinbase x402 Reference

The Coinbase x402 protocol (`github.com/coinbase/x402`) uses a Permit2-based proxy (`x402ExactPermit2Proxy` at `0x402085c248EeA27D92E8b30b2C58ed07f9E20001`). This is the EVM-canonical x402 contract for ERC-20 tokens using EIP-2612/Permit2.

USDT0 does **not** use Permit2 — it uses EIP-3009. The Flare facilitator pattern is therefore the correct choice for USDT0 on Flare.

---

## 5. FXRP Status

FXRP does **not** currently support EIP-3009. The Flare DevHub x402 page (`dev.flare.network/fxrp/token-interactions/x402-payments`) notes that MockUSDT0 is used for demonstration because FXRP lacks the required authorization methods.

FXRP support is tracked as future work, contingent on FXRP gaining EIP-3009 or an equivalent authorization path.

---

## Summary

| Question | Answer |
|---|---|
| USDT0 mainnet address | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |
| EIP-3009 supported | ✅ Yes |
| `receiveWithAuthorization` available | ✅ Yes |
| EIP-712 version | `"1"` |
| Facilitator source | Flare foundation X402Facilitator (MIT, unaudited) |
| FXRP x402 status | ❌ Not yet supported |
| Implementation unblocked | ✅ Yes |
