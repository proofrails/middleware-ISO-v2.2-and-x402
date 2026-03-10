# iso-middleware-sdk (TypeScript)

> **📊 Implementation Status**: See project root [docs/FEATURE_STATUS.md](../../docs/FEATURE_STATUS.md) for comprehensive tracking.

This is a minimal TypeScript client used by `web-alt/`.

It is intentionally lightweight and **calls the backend via a baseUrl** (in `web-alt`, baseUrl is `/api/proxy` so auth cookies never enter browser JS).

## Feature Support

| Feature | Status | Notes |
|---------|--------|-------|
| List Receipts | ✅ | With scope (mine/all) |
| Get Receipt | ✅ | Full receipt details |
| Verify Bundle | ✅ | URL and hash-based |
| Verify CID | ✅ | IPFS/Arweave support |
| Confirm Anchor | ✅ | Tenant-mode anchoring |
| Get Anchors | ✅ | Multi-chain anchor list |
| Project Config | ✅ | Get/put per-project |
| Statements | ⚠️ | Not exposed (backend ✅) |
| Refund | 🔜 | Being implemented |
| Contract ABIs | ✅ | EvidenceAnchor & Factory |

## Build

```bash
npm --prefix packages/sdk run build
```

## Usage

```ts
import IsoMiddlewareClient from "iso-middleware-sdk";

const api = new IsoMiddlewareClient({ baseUrl: "http://127.0.0.1:8000", apiKey: "..." });
const page = await api.listReceipts({ page: 1, page_size: 10, scope: "mine" });
```

## API Methods

### Receipts
```ts
// List receipts with pagination and scope
await api.listReceipts({ page: 1, page_size: 10, scope: "mine" | "all" });

// Get specific receipt
await api.getReceipt(receiptId);

// Get per-chain anchors
await api.getAnchors(receiptId);
```

### Verification
```ts
// Verify bundle by URL
await api.verifyBundle({ bundle_url: "https://..." });

// Verify bundle by hash
await api.verifyBundle({ bundle_hash: "0x..." });

// Verify CID (IPFS/Arweave)
await api.verifyCid({ cid: "Qm...", store: "ipfs", receipt_id: "..." });
```

### Tenant Anchoring
```ts
// Confirm anchor after manual on-chain submission
await api.confirmAnchor({ receipt_id: "...", chain: "flare", flare_txid: "0x..." });
```

### Project Configuration
```ts
// Get project configuration
const config = await api.getProjectConfig(projectId);

// Update project configuration
await api.putProjectConfig(projectId, updatedConfig);
```

### Refunds
```ts
// Initiate a refund for an anchored receipt
const result = await api.refund({
  original_receipt_id: "receipt-uuid",
  reason_code: "CUST"  // Optional: CUST, DUPL, TECH, FRAD
});

console.log(`Refund receipt ID: ${result.refund_receipt_id}`);
console.log(`Status: ${result.status}`);
```

### Statements
```ts
// Generate daily statement
const daily = await api.camt053("2026-01-19");

// Generate intraday statement  
const intraday = await api.camt052("2026-01-19", "09:00-17:00");
```

## Self-hosted Anchoring (Tenant Mode) ✅

In tenant mode, the middleware **does not** broadcast on-chain transactions. Instead it:
1) generates the evidence bundle → receipt becomes `awaiting_anchor`
2) you (tenant) anchor the `bundle_hash` on an EVM chain using your own contract
3) you call `POST /v1/iso/confirm-anchor` so the middleware can trustlessly validate the tx log and mark the receipt anchored.

The SDK exports minimal ABIs so you can use `ethers`/`web3`:

```ts
import IsoMiddlewareClient, { EvidenceAnchorAbi, EvidenceAnchorFactoryAbi } from "iso-middleware-sdk";

// Use ethers in your app (not bundled into this SDK)
import { BrowserProvider, Contract } from "ethers";

const api = new IsoMiddlewareClient({ baseUrl: "http://127.0.0.1:8000", apiKey: process.env.API_KEY });

// 1) Deploy (optional) via factory:
const provider = new BrowserProvider((window as any).ethereum);
const signer = await provider.getSigner();
const factory = new Contract("0x<factory>", EvidenceAnchorFactoryAbi, signer);
const deployTx = await factory.deploy();
const deployRcpt = await deployTx.wait();

// 2) Anchor evidence on your deployed EvidenceAnchor:
const anchor = new Contract("0x<anchor>", EvidenceAnchorAbi, signer);
const tx = await anchor.anchorEvidence("0x<bundle_hash>");
await tx.wait();

// 3) Confirm back to middleware (per configured chain name):
await api.confirmAnchor({ receipt_id: "<rid>", chain: "polygon", flare_txid: tx.hash });
```

Multi-chain is supported: configure `project.config.anchoring.chains[]` with multiple EVM contracts and submit a confirm for each.

## Integration with web-alt UI

The `web-alt` Next.js application uses this SDK internally with `baseUrl: "/api/proxy"` to ensure API keys remain secure in httpOnly cookies and never enter browser JavaScript.

See [web-alt/README-web-alt.md](../../web-alt/README-web-alt.md) for UI integration details.

## Contributing

When adding new features:
1. Add the method to `src/index.ts`
2. Export types from `src/contracts.ts` if needed
3. Update this README with examples
4. Update [docs/FEATURE_STATUS.md](../../docs/FEATURE_STATUS.md)
5. Test in web-alt application

## License

MIT
