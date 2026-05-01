# iso-middleware-sdk (TypeScript)

TypeScript client for the ProofRails API. Used by `web-alt/` with `baseUrl: "/api/proxy"` so API keys stay server-side.

## Build

```bash
npm --prefix packages/sdk run build
```

## Install

This package is consumed as a workspace dependency. In `web-alt/package.json`:
```json
{ "iso-middleware-sdk": "*" }
```

## Quick start

```ts
import IsoMiddlewareClient from "iso-middleware-sdk";

const api = new IsoMiddlewareClient({
  baseUrl: "http://localhost:8000",
  apiKey: process.env.API_KEY,
});

const page = await api.listReceipts({ page: 1, page_size: 10, scope: "mine" });
console.log(page.items);
```

## API methods

### Receipts

```ts
// List receipts (paginated)
const page = await api.listReceipts({ page: 1, page_size: 20, scope: "mine" });
// page: { items, total, page, page_size }

// Get one receipt
const receipt = await api.getReceipt("receipt-uuid");

// Lightweight status poll (no ISO XML blobs)
const status = await api.getReceiptStatus("receipt-uuid");

// Per-chain anchor txids
const anchors = await api.getAnchors("receipt-uuid");
```

### Verification

```ts
await api.verifyBundle({ bundle_url: "https://..." });
await api.verifyBundle({ bundle_hash: "0x..." });
await api.verifyCid({ cid: "Qm...", store: "ipfs", receipt_id: "..." });
```

### Statements

```ts
const daily = await api.camt053("2026-01-19");
const intraday = await api.camt052("2026-01-19", "09:00-17:00");
```

### Refunds

```ts
const result = await api.refund({
  original_receipt_id: "receipt-uuid",
  reason_code: "CUST",  // CUST | DUPL | TECH | FRAD
});
// result: { refund_receipt_id, status }
```

### Tenant anchoring (self-hosted mode)

```ts
// Confirm an on-chain anchor you submitted yourself
await api.confirmAnchor({
  receipt_id: "receipt-uuid",
  chain: "flare",
  flare_txid: "0x...",
});
```

### Project configuration

```ts
const config = await api.getProjectConfig("project-uuid");
await api.putProjectConfig("project-uuid", {
  anchoring: {
    execution_mode: "platform",  // or "tenant"
    chains: [{ name: "flare", contract: "0x...", rpc_url: "..." }],
  },
});
```

### Agent CRUD

```ts
const agent = await api.createAgent({
  name: "My Agent",
  wallet_address: "0x...",
  xmtp_address: "0x...",
});

const agents = await api.listAgents();
const agent = await api.getAgent("agent-uuid");
await api.updateAgent("agent-uuid", { name: "Renamed" });
await api.deleteAgent("agent-uuid");
```

### Agent anchoring config

```ts
const config = await api.getAgentAnchoringConfig("agent-uuid");

await api.updateAgentAnchoringConfig("agent-uuid", {
  auto_anchor_enabled: true,
  anchor_on_payment: false,
  anchor_wallet_address: "0x...",
  // anchor_private_key: "0x..."  — stored encrypted server-side
});
```

### Agent anchor data

```ts
// Hash arbitrary JSON and optionally submit on-chain
const result = await api.anchorAgentData("agent-uuid", {
  data: { invoice_id: "INV-001", amount: "100.00" },
  description: "Invoice proof",
  chain: "flare",           // flare | coston2 | base | sepolia
  submit_onchain: true,
});
// result: { id, agent_id, anchor_hash, chain, status, submit_onchain }

// List recent anchor records
const records = await api.listAgentAnchors("agent-uuid", 7);  // last 7 days
```

### x402 analytics

```ts
const payments = await api.listX402Payments(50);   // last N payments
const revenue = await api.getX402Revenue(7);        // last 7 days
// revenue: { total_revenue, payment_count, days, by_endpoint }
```

## Tenant anchoring — full example

```ts
import IsoMiddlewareClient, { EvidenceAnchorAbi } from "iso-middleware-sdk";
import { BrowserProvider, Contract } from "ethers";

const api = new IsoMiddlewareClient({ baseUrl: "http://localhost:8000", apiKey: "..." });

// 1. Get the bundle hash from a receipt
const receipt = await api.getReceipt("receipt-uuid");

// 2. Anchor on-chain yourself
const provider = new BrowserProvider((window as any).ethereum);
const signer = await provider.getSigner();
const contract = new Contract("0x<anchor-contract>", EvidenceAnchorAbi, signer);
const tx = await contract.anchorEvidence(receipt.bundle_hash);
await tx.wait();

// 3. Confirm back to the middleware
await api.confirmAnchor({
  receipt_id: receipt.id,
  chain: "flare",
  flare_txid: tx.hash,
});
```

## License

MIT
