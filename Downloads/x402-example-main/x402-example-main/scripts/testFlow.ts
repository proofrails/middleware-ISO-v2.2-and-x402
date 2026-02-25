/**
 * Simple x402 end-to-end test flow
 *
 * Usage:
 *   npx ts-node scripts/testFlow.ts
 */

import { ethers } from "ethers";
import "dotenv/config";

const COSTON2_RPC = process.env.COSTON2_RPC_URL || "https://coston2-api.flare.network/ext/C/rpc";
const PRIVATE_KEY = process.env.PRIVATE_KEY || "";
const TOKEN_ADDRESS = process.env.X402_TOKEN_ADDRESS || "";
const FACILITATOR_ADDRESS = process.env.X402_FACILITATOR_ADDRESS || "";
const BACKEND_URL = process.env.X402_BACKEND_URL || "http://localhost:3402";

const TOKEN_ABI = [
    "function name() view returns (string)",
    "function symbol() view returns (string)",
    "function decimals() view returns (uint8)",
    "function balanceOf(address) view returns (uint256)",
    "function mint(address to, uint256 amount)",
];

const FACILITATOR_ABI = [
    "function verifyPayment((address from, address to, address token, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)) view returns (bytes32 paymentId, bool valid)",
];

const EIP712_TYPES = {
    TransferWithAuthorization: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "value", type: "uint256" },
        { name: "validAfter", type: "uint256" },
        { name: "validBefore", type: "uint256" },
        { name: "nonce", type: "bytes32" },
    ],
};

type PaymentRequirement = {
    scheme: string;
    network: string;
    maxAmountRequired: string;
    payTo: string;
    extra: {
        tokenAddress: string;
        facilitatorAddress: string;
        chainId: number;
    };
};

async function ensureEnv() {
    if (!PRIVATE_KEY) {
        throw new Error("PRIVATE_KEY not set");
    }
    if (!TOKEN_ADDRESS) {
        throw new Error("X402_TOKEN_ADDRESS not set");
    }
    if (!FACILITATOR_ADDRESS) {
        throw new Error("X402_FACILITATOR_ADDRESS not set");
    }
}

async function main() {
    await ensureEnv();

    const provider = new ethers.JsonRpcProvider(COSTON2_RPC);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
    const token = new ethers.Contract(TOKEN_ADDRESS, TOKEN_ABI, wallet);
    const facilitator = new ethers.Contract(FACILITATOR_ADDRESS, FACILITATOR_ABI, provider);

    console.log("═".repeat(60));
    console.log("x402 Test Flow");
    console.log("═".repeat(60));
    console.log(`Backend:     ${BACKEND_URL}`);
    console.log(`Wallet:      ${wallet.address}`);
    console.log(`Token:       ${TOKEN_ADDRESS}`);
    console.log(`Facilitator: ${FACILITATOR_ADDRESS}`);
    console.log("─".repeat(60));

    // 1) Public endpoint should be free
    const publicResp = await fetch(`${BACKEND_URL}/api/public`);
    if (publicResp.status !== 200) {
        throw new Error(`Expected 200 from /api/public, got ${publicResp.status}`);
    }
    console.log("✅ /api/public reachable");

    // 2) Premium endpoint should return 402 with payment requirement
    const premiumResp = await fetch(`${BACKEND_URL}/api/premium-data`);
    if (premiumResp.status !== 402) {
        throw new Error(`Expected 402 from /api/premium-data, got ${premiumResp.status}`);
    }
    const requirement: PaymentRequirement = (await premiumResp.json()).accepts[0];
    console.log(`✅ /api/premium-data requires ${requirement.maxAmountRequired} units`);

    // 3) Ensure enough balance (minting is allowed in this demo token)
    const decimals = await token.decimals();
    const symbol = await token.symbol();
    const balance = await token.balanceOf(wallet.address);
    const requiredAmount = BigInt(requirement.maxAmountRequired);
    if (balance < requiredAmount) {
        console.log("🪙 Minting test tokens...");
        const mintAmount = ethers.parseUnits("1000", decimals);
        const mintTx = await token.mint(wallet.address, mintAmount);
        await mintTx.wait();
        console.log("✅ Minted 1000 test tokens");
    }

    // 4) Build EIP-712 authorization
    const tokenName = await token.name();
    const network = await provider.getNetwork();
    const now = Math.floor(Date.now() / 1000);
    const validAfter = now - 60;
    const validBefore = now + 300;
    const nonce = ethers.hexlify(ethers.randomBytes(32));

    const domain = {
        name: tokenName,
        version: "1",
        chainId: Number(network.chainId),
        verifyingContract: TOKEN_ADDRESS,
    };

    const message = {
        from: wallet.address,
        to: requirement.payTo,
        value: requiredAmount,
        validAfter,
        validBefore,
        nonce,
    };

    const signature = await wallet.signTypedData(domain, EIP712_TYPES, message);
    const sig = ethers.Signature.from(signature);

    // 5) Optional off-chain verify via facilitator
    const [paymentId, valid] = await facilitator.verifyPayment({
        from: wallet.address,
        to: requirement.payTo,
        token: TOKEN_ADDRESS,
        value: requiredAmount,
        validAfter,
        validBefore,
        nonce,
        v: sig.v,
        r: sig.r,
        s: sig.s,
    });
    if (!valid) {
        throw new Error("Facilitator verifyPayment returned invalid");
    }
    console.log(`✅ Authorization verified (paymentId: ${paymentId})`);

    // 6) Submit payment header and expect 200
    const paymentHeader = Buffer.from(
        JSON.stringify({
            from: wallet.address,
            to: requirement.payTo,
            token: TOKEN_ADDRESS,
            value: requiredAmount.toString(),
            validAfter: validAfter.toString(),
            validBefore: validBefore.toString(),
            nonce,
            v: sig.v,
            r: sig.r,
            s: sig.s,
        })
    ).toString("base64");

    const paidResp = await fetch(`${BACKEND_URL}/api/premium-data`, {
        headers: { "X-Payment": paymentHeader },
    });
    if (paidResp.status !== 200) {
        const errBody = await paidResp.json();
        throw new Error(`Expected 200 after payment, got ${paidResp.status}: ${JSON.stringify(errBody)}`);
    }
    const paidData = await paidResp.json();
    const paymentResponse = paidResp.headers.get("X-Payment-Response");
    if (!paymentResponse) {
        throw new Error("Missing X-Payment-Response header");
    }
    console.log(`✅ Paid access granted: ${symbol} payment settled`);
    console.log("Response:", JSON.stringify(paidData, null, 2));

    console.log("\n🎉 Test flow complete!");
}

main().catch((err) => {
    console.error("❌ Test flow failed:", err.message || err);
    process.exit(1);
});
