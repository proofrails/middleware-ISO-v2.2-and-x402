// Contract-side helpers for self-hosted anchoring (tenant mode)
//
// The SDK itself does not depend on ethers/web3. We export minimal ABIs so that
// consumers can use their preferred EVM library to deploy/call the contracts.

export const EvidenceAnchorAbi = [
  {
    type: "event",
    name: "EvidenceAnchored",
    inputs: [
      { indexed: false, name: "bundleHash", type: "bytes32" },
      { indexed: true, name: "sender", type: "address" },
      { indexed: false, name: "ts", type: "uint256" },
    ],
  },
  {
    type: "function",
    name: "anchorEvidence",
    stateMutability: "nonpayable",
    inputs: [{ name: "bundleHash", type: "bytes32" }],
    outputs: [],
  },
] as const;

export const EvidenceAnchorFactoryAbi = [
  {
    type: "event",
    name: "AnchorDeployed",
    inputs: [
      { indexed: true, name: "owner", type: "address" },
      { indexed: false, name: "anchor", type: "address" },
      { indexed: false, name: "ts", type: "uint256" },
    ],
  },
  {
    type: "function",
    name: "deploy",
    stateMutability: "nonpayable",
    inputs: [],
    outputs: [{ name: "anchor", type: "address" }],
  },
] as const;

export type ProjectAnchoringChain = {
  name: string;
  contract: string;
  rpc_url?: string | null;
  explorer_base_url?: string | null;
};

export type ProjectConfig = {
  anchoring: {
    execution_mode: "platform" | "tenant";
    chains: ProjectAnchoringChain[];
  };
};
