/**
 * Flare USDT0 x402 Agent Example
 *
 * Demonstrates how an autonomous agent pays a ProofRails premium endpoint
 * using USDT0 on Flare mainnet via EIP-3009 authorization and an x402
 * facilitator contract.
 *
 * Flow:
 *   1. Call protected endpoint → receive 402
 *   2. Select USDT0 on Flare from the accepts list
 *   3. Sign EIP-3009 TransferWithAuthorization off-chain (NOT ReceiveWithAuthorization —
 *      the facilitator calls transferWithAuthorization internally for both settlement paths)
 *   4. Submit authorization to X402Facilitator.settlePayment() — callable by anyone,
 *      including the payer. settlePaymentAsPayee() is restricted to msg.sender == payload.to
 *      (the recipient), so agents/payers must use settlePayment().
 *   5. Retry endpoint with X-PAYMENT header containing settlement_tx_hash
 *   6. Receive unlocked response
 */

import "dotenv/config";
import axios, { AxiosError } from "axios";
import { ethers, randomBytes, hexlify } from "ethers";

// ── Config ────────────────────────────────────────────────────────────────────

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";
const FLARE_RPC_URL = process.env.FLARE_RPC_URL || "https://flare-api.flare.network/ext/C/rpc";
const USDT0_ADDRESS = process.env.USDT0_ADDRESS || "0xe7cd86e13AC4309349F30B3435a9d337750fC82D";
const FACILITATOR_ADDRESS = process.env.FACILITATOR_ADDRESS!;
const AGENT_PRIVATE_KEY = process.env.AGENT_PRIVATE_KEY!;

// ── ABIs (minimal) ────────────────────────────────────────────────────────────

const USDT0_ABI = [
  "function name() view returns (string)",
  "function decimals() view returns (uint8)",
  "function balanceOf(address) view returns (uint256)",
  "function authorizationState(address authorizer, bytes32 nonce) view returns (bool)",
  "function DOMAIN_SEPARATOR() view returns (bytes32)",
];

const FACILITATOR_ABI = [
  // settlePayment — callable by anyone (including the payer). Use this in client-settled mode.
  "function settlePayment(tuple(address from, address to, address token, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s) payload) returns (bytes32 paymentId)",
  // settlePaymentAsPayee — restricted to msg.sender == payload.to (recipient only). Used in server-settled mode.
  "function settlePaymentAsPayee(tuple(address from, address to, address token, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s) payload) returns (bytes32 paymentId)",
  "event X402PaymentSettled(address indexed token, address indexed payer, address indexed recipient, uint256 amount, bytes32 nonce, bytes32 paymentId)",
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface PaymentOption {
  scheme: string;
  network: string;
  asset: string;
  payment_type: string;
  token?: string;
  facilitator?: string;
  chain_id: number;
  decimals: number;
  recipient: string;
  amount: string;
}

interface FourOhTwoResponse {
  version: string;
  error: string;
  endpoint: string;
  accepts: PaymentOption[];
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  if (!AGENT_PRIVATE_KEY) throw new Error("AGENT_PRIVATE_KEY is required");
  if (!FACILITATOR_ADDRESS) throw new Error("FACILITATOR_ADDRESS is required");

  const provider = new ethers.JsonRpcProvider(FLARE_RPC_URL);
  const wallet = new ethers.Wallet(AGENT_PRIVATE_KEY, provider);

  console.log("\n🤖  Flare USDT0 x402 Agent");
  console.log(`    Wallet:      ${wallet.address}`);
  console.log(`    API:         ${API_BASE_URL}`);
  console.log(`    Facilitator: ${FACILITATOR_ADDRESS}`);

  const endpoint = `${API_BASE_URL}/v1/x402/premium/verify-bundle`;

  // ── Step 1: Call endpoint without payment ──────────────────────────────────

  console.log("\n⏳  Step 1: Calling protected endpoint...");

  let paymentOptions: PaymentOption[] = [];

  try {
    await axios.post(endpoint, { bundle_url: "https://example.com/bundle.zip" });
    console.log("ℹ️   Endpoint returned 200 (no payment required in dev mode)");
    return;
  } catch (err) {
    const axiosErr = err as AxiosError;
    if (axiosErr.response?.status !== 402) {
      throw err;
    }
    const body = axiosErr.response.data as FourOhTwoResponse;
    console.log(`✅  Got 402 Payment Required`);
    console.log(`    Payment options: ${body.accepts.map(a => `${a.asset}/${a.network}`).join(", ")}`);
    paymentOptions = body.accepts;
  }

  // ── Step 2: Select USDT0 on Flare ─────────────────────────────────────────

  console.log("\n⏳  Step 2: Selecting USDT0 on Flare...");

  const option = paymentOptions.find(
    (o) => o.payment_type === "eip3009_facilitator" && o.network === "flare"
  );

  if (!option) {
    console.error("❌  No USDT0/Flare payment option available in 402 response");
    process.exit(1);
  }

  const tokenAddress = option.token!;
  const facilitatorAddress = option.facilitator || FACILITATOR_ADDRESS;
  const recipientAddress = option.recipient;
  const amountHuman = option.amount;
  const decimals = option.decimals ?? 6;
  const chainId = option.chain_id ?? 14;

  const rawAmount = BigInt(Math.round(parseFloat(amountHuman) * 10 ** decimals));

  console.log(`    Token:     ${tokenAddress}`);
  console.log(`    Amount:    ${amountHuman} USDT0 (raw: ${rawAmount})`);
  console.log(`    Recipient: ${recipientAddress}`);

  // ── Step 3: Sign EIP-3009 TransferWithAuthorization ─────────────────────────
  //
  // The X402Facilitator calls USDT0.transferWithAuthorization() internally for both
  // settlement paths. The EIP-712 signed type MUST be TransferWithAuthorization —
  // using ReceiveWithAuthorization would produce a different typehash and the
  // on-chain signature verification would fail.

  console.log("\n⏳  Step 3: Signing EIP-3009 TransferWithAuthorization...");

  const usdt0 = new ethers.Contract(tokenAddress, USDT0_ABI, provider);

  // Fetch token name for EIP-712 domain (do NOT hardcode — name() returns "USD₮0")
  const tokenName: string = await usdt0.name();
  console.log(`    Token name (for domain): "${tokenName}"`);

  const balance: bigint = await usdt0.balanceOf(wallet.address);
  console.log(`    USDT0 balance: ${ethers.formatUnits(balance, decimals)}`);

  if (balance < rawAmount) {
    console.error(`❌  Insufficient USDT0 balance. Have ${ethers.formatUnits(balance, decimals)}, need ${amountHuman}`);
    process.exit(1);
  }

  // Generate a random 32-byte nonce (not sequential — EIP-3009 uses bytes32 nonces)
  const nonce = hexlify(randomBytes(32)) as `0x${string}`;

  const now = Math.floor(Date.now() / 1000);
  const validAfter = BigInt(0);                 // valid immediately
  const validBefore = BigInt(now + 3600);       // expires in 1 hour

  const domain = {
    name: tokenName,
    version: "1",
    chainId: BigInt(chainId),
    verifyingContract: tokenAddress as `0x${string}`,
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

  const message = {
    from: wallet.address,
    to: recipientAddress,
    value: rawAmount,
    validAfter,
    validBefore,
    nonce,
  };

  const signature = await wallet.signTypedData(domain, types, message);
  const { v, r, s } = ethers.Signature.from(signature);

  console.log(`    Nonce: ${nonce}`);
  console.log(`    Signature: ${signature.slice(0, 20)}...`);

  // ── Step 4: Submit to X402Facilitator.settlePayment ─────────────────────────
  //
  // Agents are PAYERS, not recipients. settlePaymentAsPayee() requires
  // msg.sender == payload.to (the recipient wallet) and would revert for a payer.
  // settlePayment() is callable by anyone — including the payer — and is the
  // correct function for client-settled mode.

  console.log("\n⏳  Step 4: Submitting authorization to X402Facilitator.settlePayment()...");

  const facilitator = new ethers.Contract(facilitatorAddress, FACILITATOR_ABI, wallet);

  const payload = {
    from: wallet.address,
    to: recipientAddress,
    token: tokenAddress,
    value: rawAmount,
    validAfter,
    validBefore,
    nonce,
    v,
    r,
    s,
  };

  const settleTx = await facilitator.settlePayment(payload);
  console.log(`    Settlement TX: ${settleTx.hash}`);

  const receipt = await settleTx.wait(1);
  if (!receipt || receipt.status !== 1) {
    console.error("❌  Settlement transaction reverted");
    process.exit(1);
  }

  console.log(`✅  Settlement confirmed in block ${receipt.blockNumber}`);

  // Extract paymentId from logs
  let paymentId: string | undefined;
  for (const log of receipt.logs) {
    try {
      const parsed = facilitator.interface.parseLog(log);
      if (parsed?.name === "X402PaymentSettled") {
        paymentId = parsed.args.paymentId;
        console.log(`    Payment ID: ${paymentId}`);
      }
    } catch { /* not this contract's event */ }
  }

  // ── Step 5: Retry with X-PAYMENT header ───────────────────────────────────

  console.log("\n⏳  Step 5: Retrying endpoint with X-PAYMENT header...");

  const xPayment = JSON.stringify({
    chain: "flare",
    chain_id: chainId,
    currency: "USDT0",
    payment_type: "eip3009_facilitator",
    token: tokenAddress,
    facilitator: facilitatorAddress,
    recipient: recipientAddress,
    amount: amountHuman,
    settlement_tx_hash: settleTx.hash,
  });

  let response;
  try {
    response = await axios.post(
      endpoint,
      { bundle_url: "https://example.com/bundle.zip" },
      { headers: { "X-PAYMENT": xPayment } }
    );
  } catch (err) {
    const axiosErr = err as AxiosError;
    console.error(`❌  Endpoint returned ${axiosErr.response?.status}`);
    console.error(axiosErr.response?.data);
    process.exit(1);
  }

  console.log(`✅  Endpoint unlocked! Status: ${response.status}`);
  console.log("\n📦  Response:", JSON.stringify(response.data, null, 2));

  // ── Step 6: Payment evidence ───────────────────────────────────────────────

  console.log("\n🧾  Payment evidence:");
  console.log(`    Network:          Flare mainnet (chainId ${chainId})`);
  console.log(`    Token:            USDT0 ${tokenAddress}`);
  console.log(`    Amount:           ${amountHuman} USDT0`);
  console.log(`    Payer:            ${wallet.address}`);
  console.log(`    Recipient:        ${recipientAddress}`);
  console.log(`    Facilitator:      ${facilitatorAddress}`);
  console.log(`    Settlement TX:    ${settleTx.hash}`);
  console.log(`    Payment ID:       ${paymentId ?? "n/a"}`);
  console.log(`    Explorer:         https://flarescan.com/tx/${settleTx.hash}`);
}

main().catch((err) => {
  console.error("\n❌  Fatal error:", err.message || err);
  process.exit(1);
});
