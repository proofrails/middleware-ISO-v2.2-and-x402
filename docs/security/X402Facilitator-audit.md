# X402Facilitator — Internal Security Audit

**Date:** 2026-05-06  
**Auditor:** Internal review (Claude Code)  
**Commit scope:** `contracts/X402Facilitator.sol`, `contracts/test/MockEIP3009Token.sol`, `hardhat.config.js`, `scripts/deploy_x402_facilitator.js`  
**Automated tools run:** Slither (not installed), Mythril (not installed), Forge compiler warnings  
**Disclaimer:** This is an internal review, not a substitute for a professional third-party audit. **Do not deploy to Flare mainnet with significant value without a commissioned external audit.**

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 1 | Fixed |
| High | 1 | Fixed |
| Medium | 1 | Documented (design trade-off) |
| Low | 4 | Fixed |
| Informational | 3 | Fixed / Noted |
| Build Bug | 1 | Fixed |

---

## Findings

### [CRITICAL-1] Fee mechanism declared but never implemented

**File:** `X402Facilitator.sol`  
**Status:** Fixed — fee state variables and functions removed entirely

**Description:**  
The original contract declared `feeBps`, `feeRecipient`, `setFeeBps()`, and `setFeeRecipient()`, and accepted `_feeBps` and `_feeRecipient` in the constructor. However, neither `settlePaymentAsPayee` nor `settlePayment` used these values. Settlements transferred the full `payload.value` to `payload.to` with no deduction, regardless of `feeBps`.

An operator deploying with `feeBps = 50` (0.5%) would believe fees were being collected. No fees were collected. This is a silent failure with no error or event to signal the misconfiguration.

**Fix:**  
Removed `feeBps`, `feeRecipient`, and all related setters/events. Constructor now takes only `address _owner`. Implementing protocol fees with EIP-3009 requires a different flow (payer signs to the facilitator contract, which then splits and forwards) — this can be added in a v2 with proper design.

---

### [HIGH-1] Checks-Effects-Interactions (CEI) violation

**File:** `X402Facilitator.sol`, `settlePaymentAsPayee` and `settlePayment`  
**Status:** Fixed

**Description:**  
Both settlement functions wrote state (`_record`) *after* the external call to the token contract. This violates the CEI pattern. Although `nonReentrant` prevented immediate exploitation, removing or bypassing `nonReentrant` (or using a malicious token) could enable reentrancy to settle the same payment twice before the record is written.

**Original flow (vulnerable):**
```
CHECK  payments[paymentId].settled == false
CHECK  token.authorizationState == false
INTERACTION  token.receiveWithAuthorization(...)  ← external call
EFFECT  _record(paymentId, ...)                   ← state write AFTER
```

**Fixed flow:**
```
CHECK  payments[paymentId].settled == false
CHECK  token.authorizationState == false
EFFECT  _record(paymentId, ...)                   ← state write BEFORE external call
INTERACTION  token.receiveWithAuthorization(...)
```

In Solidity, if the external call reverts, the entire transaction reverts including the state write, so the CEI order is safe.

---

### [MEDIUM-1] Griefing via front-running of `settlePaymentAsPayee`

**File:** `X402Facilitator.sol`  
**Status:** Documented — design trade-off, not fixable without removing `settlePayment`

**Description:**  
`settlePayment` (using `transferWithAuthorization`) is callable by anyone. An attacker can observe a pending `settlePaymentAsPayee` transaction in the mempool and front-run it by calling `settlePayment` with the same payload and higher gas.

Result:
- The attacker's `settlePayment` settles the payment (funds go to `payload.to` — the correct recipient, because EIP-3009 sigs bind the destination address)
- The original `settlePaymentAsPayee` reverts with `AuthorizationAlreadyUsed`
- The payee wastes gas; no funds are stolen

This is a griefing attack (wasted gas, tx reversion) not a theft vector. On Flare, mempool visibility is limited by the C-Chain architecture, reducing practical risk.

**Mitigations documented in contract NatSpec:**
- Use a private mempool / FastLane on mainnet for `settlePaymentAsPayee` calls
- The `settlePaymentAsPayee` path is preferred; `settlePayment` should only be used for server-submitted mode where front-running is not a concern

---

### [LOW-1] Constructor missing zero-address check for owner

**File:** `X402Facilitator.sol`  
**Status:** Fixed

**Original:**
```solidity
constructor(address _feeRecipient, uint256 _feeBps) Ownable(msg.sender) {
    feeRecipient = _feeRecipient; // no zero-address check
```

**Fixed:**
```solidity
constructor(address _owner) Ownable(_owner) {
    if (_owner == address(0)) revert ZeroAddress();
```

---

### [LOW-2] Zero-value payments accepted when no per-token minimum is set

**File:** `X402Facilitator.sol`, `_validateAmount`  
**Status:** Fixed

**Description:**  
When `minimumAmounts[token] == 0` (default), the original check `if (min > 0 && value < min)` allowed zero-value payments through. An attacker could spam `X402PaymentSettled` events with no economic cost (just gas), polluting off-chain indexers.

**Fix:** Added `DEFAULT_MIN = 1` constant. Effective minimum is `max(minimumAmounts[token], DEFAULT_MIN)`. Applied consistently in both `_validateAmount` and `verifyPayment`.

---

### [LOW-3] `removeSupportedToken` did not clear `minimumAmounts`

**File:** `X402Facilitator.sol`  
**Status:** Fixed

**Description:**  
Removing a token left its `minimumAmounts` entry intact. If the token is re-added, the old minimum silently reactivates. Unexpected behavior for operators.

**Fix:** `removeSupportedToken` now also sets `minimumAmounts[token] = 0`.

---

### [LOW-4] No emergency pause mechanism

**File:** `X402Facilitator.sol`  
**Status:** Fixed

**Description:**  
The original contract had no way to halt new settlements if a critical bug was discovered or an active attack was occurring. The only mitigation was removing supported tokens one by one.

**Fix:** Contract now inherits OpenZeppelin `Pausable`. Both `settlePaymentAsPayee` and `settlePayment` are guarded with `whenNotPaused`. Owner can call `pause()` / `unpause()`.

---

### [INFO-1] `PaymentRecord` did not store the EIP-3009 nonce

**File:** `X402Facilitator.sol`  
**Status:** Fixed

**Description:**  
The on-chain record omitted the `nonce` field, making it impossible to cross-reference a `PaymentRecord` with the token's `authorizationState(authorizer, nonce)` mapping without re-computing.

**Fix:** Added `bytes32 nonce` to `PaymentRecord`. Tests updated to assert `record.nonce` is correctly stored.

---

### [INFO-2] `_paymentId` omits `validAfter` / `validBefore`

**File:** `X402Facilitator.sol`, `_paymentId`  
**Status:** Accepted (informational only)

**Description:**  
`paymentId = keccak256(abi.encode(from, to, token, value, nonce))` does not include the validity window. Two authorizations with identical parameters but different windows would produce the same `paymentId`. In practice this cannot happen because EIP-3009 nonces are one-time-use per `(authorizer, nonce)` on the token — the nonce provides uniqueness. No change made.

---

### [INFO-3] No upgrade path

**File:** `X402Facilitator.sol`  
**Status:** Accepted

**Description:**  
The contract is not upgradeable (no proxy pattern). This is intentional — it eliminates proxy-related attack surfaces (storage collision, selector clashing). If bugs are found post-deployment, a new contract must be deployed and the backend pointed to the new address. Operators should keep `X402_FLARE_FACILITATOR_ADDRESS` in env and redeploy as needed.

---

### [BUILD-1] Hardhat config ESM import resolves incorrectly

**File:** `hardhat.config.js`  
**Status:** Fixed

**Description:**  
```javascript
import { HardhatUserConfig } from "hardhat/config"; // ❌ missing .js extension
```
Node ESM (the project uses `"type": "module"`) requires explicit `.js` extensions for relative and bare specifier imports. Without it, `npx hardhat compile` fails with `ERR_MODULE_NOT_FOUND`.

**Fix:**
```javascript
import { HardhatUserConfig } from "hardhat/config.js"; // ✅
```

---

## MockEIP3009Token — notes

`MockEIP3009Token.sol` is test-only and intentionally skips EIP-712 signature verification. No security issues for a test mock. **Must never be deployed to mainnet.** The contract's `DOMAIN_SEPARATOR()` returns `bytes32(0)`, which would be an obvious red flag if it were ever used in production.

---

## What was NOT checked (requires external audit)

The following are out of scope for an internal review and require a professional audit:

1. **Formal verification** of the settlement invariant: "for any settled paymentId, the corresponding token transfer completed exactly once."
2. **EVM-level storage layout** — confirm no slot collisions with OpenZeppelin inherited contracts (`Ownable`, `ReentrancyGuard`, `Pausable`).
3. **Gas griefing** — whether the revert path in `settlePaymentAsPayee` could be exploited to drain the caller's gas beyond wasted-gas amounts.
4. **USDT0 contract behavior on Flare** — specifically, whether `TetherTokenOFTExtension` implements `receiveWithAuthorization` with strict `msg.sender == to` enforcement as expected.
5. **Timestamp manipulation** — Flare validators can manipulate `block.timestamp` by ~90 seconds. Authorizations with very short `validBefore` windows could be affected.

---

## Pre-mainnet checklist

- [ ] Deploy to Coston2 testnet and run full integration test suite
- [ ] Commission external audit (e.g., OpenZeppelin, Trail of Bits, Certik)
- [ ] Use a multisig (Gnosis Safe) as the owner address — not a single EOA
- [ ] Verify source code on Flarescan after deployment
- [ ] Set per-token minimum via `setMinimumAmount` before announcing live
- [ ] Test `pause()` and `unpause()` on testnet with the owner multisig
- [ ] Document the contract address in `X402_FLARE_FACILITATOR_ADDRESS` env var
- [ ] Confirm USDT0 `receiveWithAuthorization` is live on Flare mainnet (not just testnet)
