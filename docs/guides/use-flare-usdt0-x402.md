# How to Pay with USDT0 on Flare via x402

This guide shows how to configure ProofRails and how an agent (or client) pays a premium endpoint using USDT0 on Flare mainnet via EIP-3009 authorization and an x402-compatible facilitator contract.

---

## Prerequisites

- USDT0 balance on Flare mainnet
- A deployed `X402Facilitator` contract (see `docs/FLARE_INTEGRATION.md`)
- ProofRails configured with `X402_FLARE_FACILITATOR_ADDRESS` and `X402_USDT0_RECIPIENT`

---

## Configuration

In your `.env` or Railway environment:

```bash
X402_ENABLE_FLARE_USDT0=true
X402_FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
X402_FLARE_CHAIN_ID=14
X402_USDT0_FLARE_ADDRESS=0xe7cd86e13AC4309349F30B3435a9d337750fC82D
X402_USDT0_DECIMALS=6
X402_USDT0_AMOUNT=0.001
X402_FLARE_FACILITATOR_ADDRESS=0xYourDeployedFacilitator
X402_USDT0_RECIPIENT=0xYourRecipientWalletOnFlare
X402_FLARE_CONFIRMATIONS=1
X402_SETTLEMENT_MODE=client
```

---

## Step-by-Step: Paying a Premium Endpoint

### Step 1 — Call the endpoint without payment

```bash
curl -X POST https://your-instance.railway.app/v1/x402/premium/verify-bundle \
  -H "Content-Type: application/json" \
  -d '{"bundle_url": "https://example.com/bundle.zip"}'
```

**Response (402 Payment Required):**

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

### Step 2 — Sign EIP-3009 TransferWithAuthorization

The `X402Facilitator` calls `USDT0.transferWithAuthorization()` internally for both settlement paths. The EIP-712 signed type must be `TransferWithAuthorization` — using `ReceiveWithAuthorization` would produce a different typehash and the on-chain verification would fail.

```typescript
import { ethers, randomBytes, hexlify } from "ethers";

const provider = new ethers.JsonRpcProvider("https://flare-api.flare.network/ext/C/rpc");
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

const usdt0 = new ethers.Contract(
  "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
  ["function name() view returns (string)"],
  provider
);

// Always fetch name on-chain — do NOT hardcode for EIP-712 domain (returns "USD₮0")
const tokenName = await usdt0.name();

const domain = {
  name: tokenName,
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

const nonce = hexlify(randomBytes(32));
const now = Math.floor(Date.now() / 1000);
const rawAmount = 1000n; // 0.001 USDT0 (6 decimals)

const message = {
  from: wallet.address,
  to: "0xRecipient",
  value: rawAmount,
  validAfter: 0n,
  validBefore: BigInt(now + 3600),
  nonce,
};

const signature = await wallet.signTypedData(domain, types, message);
const { v, r, s } = ethers.Signature.from(signature);
```

### Step 3 — Submit to X402Facilitator.settlePayment

As a payer/client, call `settlePayment()` — callable by anyone including the payer. `settlePaymentAsPayee()` is restricted to `msg.sender == payload.to` (the recipient) and would revert if called by the payer.

```typescript
const facilitator = new ethers.Contract(
  "0xFacilitator",
  [
    "function settlePayment(tuple(address from, address to, address token, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)) returns (bytes32)"
  ],
  wallet
);

const tx = await facilitator.settlePayment({
  from: wallet.address,
  to: "0xRecipient",
  token: "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
  value: rawAmount,
  validAfter: 0n,
  validBefore: BigInt(now + 3600),
  nonce,
  v,
  r,
  s,
});

const receipt = await tx.wait(1);
```

### Step 4 — Retry with X-PAYMENT header

```typescript
const xPayment = JSON.stringify({
  chain: "flare",
  chain_id: 14,
  currency: "USDT0",
  payment_type: "eip3009_facilitator",
  token: "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
  facilitator: "0xFacilitator",
  recipient: "0xRecipient",
  amount: "0.001",
  settlement_tx_hash: tx.hash,
});

const response = await fetch(
  "https://your-instance.railway.app/v1/x402/premium/verify-bundle",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-PAYMENT": xPayment,
    },
    body: JSON.stringify({ bundle_url: "https://example.com/bundle.zip" }),
  }
);

// 200 OK — endpoint unlocked
const data = await response.json();
```

---

## Agentic Payments

Autonomous AI agents (LLM-based, XMTP, or HTTP-based) follow the same four-step flow. The key design point: the agent is the **payer**, so it must call `settlePayment()` (open to anyone) — not `settlePaymentAsPayee()`, which is restricted to the recipient.

### How an agent handles 402 automatically

```typescript
async function callWithPayment(endpoint: string, body: unknown, wallet: ethers.Wallet) {
  // 1. Try the request
  try {
    return await axios.post(endpoint, body);
  } catch (err) {
    const e = err as AxiosError;
    if (e.response?.status !== 402) throw err;

    // 2. Parse accepted payment options
    const { accepts } = e.response.data as { accepts: PaymentOption[] };

    // 3. Prefer USDT0 on Flare; fall back to USDC or FLR
    const option =
      accepts.find(o => o.payment_type === "eip3009_facilitator") ??
      accepts.find(o => o.payment_type === "erc20_transfer") ??
      accepts[0];

    if (!option) throw new Error("No supported payment option");

    // 4. Pay (implements USDT0 path — see full example for USDC/FLR)
    const settlementTxHash = await payWithUSDT0(option, wallet);

    // 5. Retry with proof
    return axios.post(endpoint, body, {
      headers: {
        "X-PAYMENT": JSON.stringify({
          chain: "flare",
          chain_id: 14,
          currency: "USDT0",
          payment_type: "eip3009_facilitator",
          token: option.token,
          facilitator: option.facilitator,
          recipient: option.recipient,
          amount: option.amount,
          settlement_tx_hash: settlementTxHash,
        }),
      },
    });
  }
}
```

### Important: settlement function for payers

| Who calls | Correct function | Reason |
|---|---|---|
| Agent / payer | `settlePayment(payload)` | Callable by anyone |
| ProofRails server (settler == recipient) | `settlePaymentAsPayee(payload)` | Requires `msg.sender == payload.to` |

A payer calling `settlePaymentAsPayee` will get `InvalidPaymentPayload` revert.

## Complete Agent Example

See `examples/flare-usdt0-x402-agent/src/index.ts` for a complete TypeScript agent that handles the full flow automatically. It demonstrates payment option selection, balance check, EIP-712 signing, `settlePayment` call, and endpoint retry.

```bash
cd examples/flare-usdt0-x402-agent
cp .env.example .env
# Fill in FACILITATOR_ADDRESS and AGENT_PRIVATE_KEY
npm install
npm run dev
```

---

## Error Responses

| HTTP | `detail` | Meaning |
|---|---|---|
| 402 | — | No payment provided |
| 400 | `invalid_usdt0_payment_header` | Cannot parse X-PAYMENT |
| 400 | `wrong_token_address` | Token in header doesn't match server config |
| 400 | `wrong_facilitator_address` | Facilitator in header doesn't match server config |
| 400 | `missing_settlement_tx_hash` | Client mode but no hash provided |
| 400 | `usdt0_payment_not_enabled` | Feature toggle off |
| 400 | `facilitator_not_configured` | Server missing `X402_FLARE_FACILITATOR_ADDRESS` |
| 403 | `payment_verification_failed:transaction_not_found` | TX not on chain |
| 403 | `payment_verification_failed:token_mismatch` | Wrong token in event |
| 403 | `payment_verification_failed:wrong_recipient` | Wrong recipient in event |
| 403 | `payment_verification_failed:insufficient_amount` | Amount too small |
| 403 | `payment_verification_failed:wrong_facilitator` | TX sent to wrong contract |
| 409 | `payment_already_used` | TX hash already recorded |
| 409 | `nonce_already_used` | EIP-3009 nonce already recorded |
