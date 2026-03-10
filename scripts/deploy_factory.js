// Deploy EvidenceAnchorFactory using ethers + local private key
// Usage:
//   node scripts/deploy_factory.js --rpc <RPC_URL> --pk <PRIVATE_KEY>
//
// Note: For production, use a safer deploy pipeline.

import { ethers } from "ethers";
import fs from "fs";
import path from "path";

function arg(name, fallback = null) {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

const rpc = arg("--rpc", process.env.FLARE_RPC_URL);
const pk = arg("--pk", process.env.ANCHOR_PRIVATE_KEY);

if (!rpc || !pk) {
  console.error("Missing --rpc or --pk (or env FLARE_RPC_URL/ANCHOR_PRIVATE_KEY)");
  process.exit(1);
}

const provider = new ethers.JsonRpcProvider(rpc);
const wallet = new ethers.Wallet(pk, provider);

const solPath = path.join("contracts", "EvidenceAnchorFactory.sol");
const sol = fs.readFileSync(solPath, "utf8");

// Minimal inline compiler using solcjs is already installed.
import solc from "solc";

const input = {
  language: "Solidity",
  sources: {
    "EvidenceAnchorFactory.sol": { content: sol },
    "EvidenceAnchor.sol": { content: fs.readFileSync(path.join("contracts", "EvidenceAnchor.sol"), "utf8") },
  },
  settings: {
    outputSelection: {
      "*": {
        "*": ["abi", "evm.bytecode.object"],
      },
    },
  },
};

const out = JSON.parse(solc.compile(JSON.stringify(input)));
if (out.errors?.length) {
  const fatal = out.errors.filter((e) => e.severity === "error");
  out.errors.forEach((e) => console.error(e.formattedMessage));
  if (fatal.length) process.exit(1);
}

const c = out.contracts["EvidenceAnchorFactory.sol"]["EvidenceAnchorFactory"];
const abi = c.abi;
const bytecode = "0x" + c.evm.bytecode.object;

const factory = new ethers.ContractFactory(abi, bytecode, wallet);
console.log("Deploying EvidenceAnchorFactory...");
const contract = await factory.deploy();
await contract.waitForDeployment();
const addr = await contract.getAddress();
console.log("Deployed:", addr);

fs.writeFileSync(
  path.join("contracts", "EvidenceAnchorFactory.deployed.json"),
  JSON.stringify({ address: addr, rpc, deployed_at: new Date().toISOString() }, null, 2)
);

fs.writeFileSync(path.join("contracts", "EvidenceAnchorFactory.abi.json"), JSON.stringify(abi, null, 2));
