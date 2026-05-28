# Flare Integration

ProofRails integrates with Flare mainnet for two purposes:

1. **Evidence anchoring** — ISO 20022 payment bundles are anchored on Flare via the `EvidenceAnchor` contract.
2. **x402 payments** — Paid endpoints accept USDT0 on Flare (EIP-3009 facilitator) and native FLR.

---

## Chain Details

| Field | Value |
|---|---|
| Chain | Flare mainnet |
| Chain ID | 14 |
| RPC | https://flare-api.flare.network/ext/C/rpc |
| Explorer | https://flarescan.com |

---

## USDT0 x402 Payments on Flare

### Token

| Field | Value |
|---|---|
| Contract | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` |
| Name | USD₮0 |
| Symbol | USDT0 |
| Decimals | 6 |
| EIP-3009 | Supported (`transferWithAuthorization`, `receiveWithAuthorization`) |
| Source | Tether/LayerZero OFT deployment |

### Facilitator

The `X402Facilitator` contract handles settlement. Deploy your own instance (see `scripts/deploy_x402_facilitator.js`) and set `X402_FLARE_FACILITATOR_ADDRESS`.

| Field | Value |
|---|---|
| Source | `contracts/X402Facilitator.sol` |
| Audit | Unaudited — built on OpenZeppelin Ownable + ReentrancyGuard |
| Settlement method | `settlePaymentAsPayee` (receiveWithAuthorization) |

### Signing Flow

The `X402Facilitator` calls `USDT0.transferWithAuthorization()` internally. The EIP-712 signed type must be `TransferWithAuthorization` — using `ReceiveWithAuthorization` produces a different typehash and the on-chain signature verification fails.

```typescript
const domain = {
  name: await usdt0.name(),  // "USD₮0" — always read on-chain, do NOT hardcode
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

const sig = await wallet.signTypedData(domain, types, {
  from: wallet.address,
  to: recipientAddress,
  value: rawAmount,         // integer, 6 decimals
  validAfter: 0n,
  validBefore: BigInt(now + 3600),
  nonce: hexlify(randomBytes(32)),  // random bytes32
});
```

**Settlement function for payers (client-settled mode):** call `facilitator.settlePayment(payload)` — callable by anyone including the payer. `settlePaymentAsPayee()` requires `msg.sender == payload.to` (recipient only) and will revert if called by the payer.

### Server Verification Flow

ProofRails verifies client-submitted settlement transactions by:
1. Fetching the Flare transaction receipt.
2. Confirming the `to` address matches the configured facilitator.
3. Parsing the `X402PaymentSettled(token, payer, recipient, amount, nonce, paymentId)` event.
4. Validating token, recipient, and amount match configuration.
5. Checking `tx_hash` and `nonce` are not already recorded (replay protection).
6. Recording payment in `x402_payments` with all chain/token metadata.

### Environment Variables

```bash
X402_ENABLE_FLARE_USDT0=true
X402_FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
X402_FLARE_CHAIN_ID=14
X402_USDT0_FLARE_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D
X402_USDT0_DECIMALS=6
X402_USDT0_AMOUNT=0.001
X402_FLARE_FACILITATOR_ADDRESS=0xYourDeployedFacilitator
X402_USDT0_RECIPIENT=0xYourRecipient
X402_FLARE_CONFIRMATIONS=1
X402_SETTLEMENT_MODE=client
# X402_SETTLER_PRIVATE_KEY=   # only for server-settlement mode
```

### Security Notes

| Risk | Mitigation |
|---|---|
| Front-running | `receiveWithAuthorization` requires `msg.sender == to` |
| Nonce reuse | Nonce stored in `x402_payments`; duplicate rejected with 409 |
| Settlement TX replay | `tx_hash` unique-indexed in DB; duplicate rejected with 409 |
| Token mismatch | Server validates `token` from event matches config |
| Recipient mismatch | Server validates `recipient` from event matches config |
| Expired authorization | Facilitator contract enforces `validBefore` on-chain |
| Insufficient amount | Facilitator enforces `minimumAmounts[token]` on-chain |
| Integer overflow | Raw amounts stored as `String`; Decimal used for human display |
| Floating point | All token math uses Python `Decimal`; no floats |
| Server key exposure | Optional — only required if `X402_SETTLEMENT_MODE=server` |

---

## Native FLR Payments

Simpler HTTP 402 gate using native FLR. Not EIP-3009.

```bash
X402_ENABLE_FLARE_NATIVE_FLR=true
X402_FLR_AMOUNT=0.05
X402_FLR_RECIPIENT=0xYourRecipient
```

---

## Deploying the Facilitator

```bash
# Compile (requires Hardhat)
npx hardhat compile

# Deploy to Coston2 testnet first
DEPLOYER_PRIVATE_KEY=0x... \
X402_RECIPIENT_ADDRESS=0x... \
node scripts/deploy_x402_facilitator.js --network coston2

# Deploy to Flare mainnet (only after testing on Coston2)
DEPLOYER_PRIVATE_KEY=0x... \
X402_RECIPIENT_ADDRESS=0x... \
USDT0_FLARE_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D \
node scripts/deploy_x402_facilitator.js --network flare
```

The deployment artifact is written to `deployments/flare/x402-facilitator.json`.

---

## Evidence Anchoring

Existing functionality — see `README.md` for details.

| Field | Value |
|---|---|
| Contract | `EvidenceAnchor` |
| Default address | `0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8` |
| ABI | `contracts/EvidenceAnchor.abi.json` |
