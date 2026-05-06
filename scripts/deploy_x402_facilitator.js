/**
 * Deployment script for X402Facilitator on Flare / Coston2.
 *
 * Usage:
 *   node scripts/deploy_x402_facilitator.js --network flare
 *   node scripts/deploy_x402_facilitator.js --network coston2
 *
 * Required env vars:
 *   DEPLOYER_PRIVATE_KEY
 *   X402_RECIPIENT_ADDRESS  — wallet that will OWN the contract (use a multisig on mainnet)
 *   FLARE_RPC_URL   (default: https://flare-api.flare.network/ext/C/rpc)
 *   COSTON2_RPC_URL (default: https://coston2-api.flare.network/ext/C/rpc)
 *   USDT0_FLARE_ADDRESS  (mainnet token; defaults to known USDT0 address)
 *   MOCK_USDT0_COSTON2   (testnet mock token address, optional)
 */

import { ethers } from "ethers";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

// ── Config ────────────────────────────────────────────────────────────────────

const NETWORKS = {
  flare: {
    rpc: process.env.FLARE_RPC_URL || "https://flare-api.flare.network/ext/C/rpc",
    chainId: 14,
    tokenAddress: process.env.USDT0_FLARE_ADDRESS || "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
    explorerBase: "https://flarescan.com",
  },
  coston2: {
    rpc: process.env.COSTON2_RPC_URL || "https://coston2-api.flare.network/ext/C/rpc",
    chainId: 114,
    tokenAddress: process.env.MOCK_USDT0_COSTON2 || null,
    explorerBase: "https://coston2.testnet.flarescan.com",
  },
};

// ── ABI ───────────────────────────────────────────────────────────────────────

const FACILITATOR_ABI = [
  "constructor(address _owner)",
  "function addSupportedToken(address token) external",
  "function setMinimumAmount(address token, uint256 amount) external",
  "function pause() external",
  "function unpause() external",
  "function supportedTokens(address) view returns (bool)",
  "event X402PaymentSettled(address indexed token, address indexed payer, address indexed recipient, uint256 amount, bytes32 nonce, bytes32 paymentId)",
];

// Load compiled bytecode from Hardhat artifact
function loadBytecode() {
  const artifactPath = join(ROOT, "artifacts", "contracts", "X402Facilitator.sol", "X402Facilitator.json");
  if (!existsSync(artifactPath)) {
    console.error("No compiled artifact found. Run: npx hardhat compile");
    console.error("Artifact expected at:", artifactPath);
    process.exit(1);
  }
  const artifact = JSON.parse(readFileSync(artifactPath, "utf8"));
  return artifact.bytecode;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  const networkName = process.argv.includes("--network")
    ? process.argv[process.argv.indexOf("--network") + 1]
    : "coston2";

  const network = NETWORKS[networkName];
  if (!network) {
    console.error(`Unknown network: ${networkName}. Use 'flare' or 'coston2'.`);
    process.exit(1);
  }

  const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  const ownerAddress = process.env.X402_RECIPIENT_ADDRESS; // owner of the deployed contract

  if (!privateKey) { console.error("Missing DEPLOYER_PRIVATE_KEY"); process.exit(1); }
  if (!ownerAddress) { console.error("Missing X402_RECIPIENT_ADDRESS (contract owner)"); process.exit(1); }

  console.log(`\nDeploying X402Facilitator to ${networkName} (chainId ${network.chainId})`);
  console.log(`  RPC:    ${network.rpc}`);
  console.log(`  Owner:  ${ownerAddress}`);

  const provider = new ethers.JsonRpcProvider(network.rpc);
  const wallet = new ethers.Wallet(privateKey, provider);
  const deployer = wallet.address;
  console.log(`  Signer: ${deployer}`);

  const bytecode = loadBytecode();
  const factory = new ethers.ContractFactory(FACILITATOR_ABI, bytecode, wallet);

  console.log("\nDeploying...");
  const contract = await factory.deploy(ownerAddress);
  const receipt = await contract.deploymentTransaction().wait(1);

  const facilitatorAddress = await contract.getAddress();
  const txHash = receipt.hash;
  const blockNumber = receipt.blockNumber;
  const timestamp = new Date().toISOString();

  console.log(`\nDeployed!`);
  console.log(`  Facilitator: ${facilitatorAddress}`);
  console.log(`  TX:          ${txHash}`);
  console.log(`  Block:       ${blockNumber}`);
  console.log(`  Explorer:    ${network.explorerBase}/address/${facilitatorAddress}`);

  // Register token if known
  if (network.tokenAddress) {
    console.log(`\nRegistering token ${network.tokenAddress}...`);
    const tx = await contract.addSupportedToken(network.tokenAddress);
    await tx.wait(1);
    console.log(`Token registered`);

    // 0.001 USDT0 = 1000 raw units (6 decimals)
    const minAmount = BigInt(1000);
    const tx2 = await contract.setMinimumAmount(network.tokenAddress, minAmount);
    await tx2.wait(1);
    console.log(`Minimum amount set: ${minAmount} (0.001 USDT0)`);
  }

  // Write deployment artifact
  const artifactDir = join(ROOT, "deployments", networkName);
  mkdirSync(artifactDir, { recursive: true });

  const artifact = {
    network: networkName,
    chainId: network.chainId,
    facilitator: facilitatorAddress,
    token: network.tokenAddress,
    owner: ownerAddress,
    deployer,
    txHash,
    blockNumber,
    timestamp,
    explorerUrl: `${network.explorerBase}/address/${facilitatorAddress}`,
  };

  const artifactPath = join(artifactDir, "x402-facilitator.json");
  writeFileSync(artifactPath, JSON.stringify(artifact, null, 2));
  console.log(`\nArtifact written to: ${artifactPath}`);

  console.log("\nConstructor arg for source verification:");
  console.log(`  ${ownerAddress}`);

  return artifact;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
