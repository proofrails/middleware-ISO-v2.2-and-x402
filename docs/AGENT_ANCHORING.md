# Agent Anchoring — Technical Documentation

This document covers the architecture, configuration, and internals of the agent anchoring system. For UI walkthroughs and SDK quick-starts, see the main [README](../README.md).

---

## Overview

Agent Anchoring allows autonomous AI agents to create cryptographically verifiable audit trails by writing SHA-256 hashes of payment data to EVM smart contracts. The system supports both automatic (payment-triggered) and manual anchoring, with built-in retry logic, nonce management, and multi-chain support.

---

## Architecture

### Data Flow

```
Agent / API caller
      │
      ▼
POST /v1/agents/{id}/anchor   (or auto-trigger on x402 payment)
      │
      ▼
┌──────────────────────────┐
│  API Server (FastAPI)    │
│  - Creates AgentAnchor   │
│  - Enqueues to Redis     │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐     ┌─────────────────────────┐
│  Default Worker          │     │  Anchor Worker           │
│  (queue: "default")      │     │  (queue: "anchor")       │
│  - Compliance checks     │     │  - Sends on-chain tx     │
│  - ISO XML generation    │     │  - Manages nonces        │
│  - Evidence ZIP bundling │     │  - Batch throttling      │
│  - SHA-256 hashing       │     └──────────┬──────────────┘
└──────────┬───────────────┘                │
           │                                ▼
           │                    ┌─────────────────────────┐
           │                    │  AnchorPoller (thread)   │
           │                    │  - Polls tx receipts     │
           │                    │  - Finalises receipts    │
           │                    │  - Re-enqueues failures  │
           │                    └──────────┬──────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────────┐
│  EVM Chain (Flare / Ethereum / Base / Optimism)  │
│  EvidenceAnchor.anchorEvidence(bytes32)           │
│  → emits EvidenceAnchored(bundleHash, sender, ts) │
└──────────────────────────────────────────────────┘
```

### Key Components

**API Layer** (`app/api/routes/agent_anchoring.py`): REST endpoints for triggering anchors, listing history, and configuring auto-anchoring.

**Anchor Module** (`app/anchor.py`): Python/web3 implementation for building, signing, and sending anchor transactions. Supports EIP-1559 fee estimation with legacy gas price fallback.

**Anchor Node** (`app/anchor_node.py`): Alternative path that shells out to Node.js scripts (`scripts/anchor.js`, `scripts/find.js`) for anchoring and lookup. Used as a fallback.

**Anchor Poller** (`app/anchor_poller.py`): Background daemon thread that runs inside the anchor worker process. Polls for transaction confirmations, finalises receipts, and re-enqueues failed sends.

**Nonce Manager** (`app/nonce_manager.py`): Redis-backed atomic nonce coordination to prevent nonce collisions when the anchor worker processes multiple receipts.

---

## Smart Contracts

### EvidenceAnchor

The core contract. Minimal by design — a single function that emits an event:

```solidity
contract EvidenceAnchor {
    event EvidenceAnchored(bytes32 bundleHash, address indexed sender, uint256 ts);

    function anchorEvidence(bytes32 bundleHash) external {
        emit EvidenceAnchored(bundleHash, msg.sender, block.timestamp);
    }
}
```

Deployed on Flare mainnet at: `0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8`

The ABI is stored at `contracts/EvidenceAnchor.abi.json`. If the file is missing, the code falls back to a hardcoded minimal ABI.

### EvidenceAnchorFactory

Deploys new `EvidenceAnchor` instances. Useful when tenants want their own isolated contract:

```solidity
contract EvidenceAnchorFactory {
    event AnchorDeployed(address indexed owner, address anchor, uint256 ts);

    function deploy() external returns (address anchor) {
        EvidenceAnchor a = new EvidenceAnchor();
        anchor = address(a);
        emit AnchorDeployed(msg.sender, anchor, block.timestamp);
    }
}
```

### FactoryRegistry

Central governance contract for tracking, deprecating, and reactivating factory deployments. Provides `isValidFactory()`, `getActiveFactories()`, and ownership transfer.

---

## Database Models

### AgentAnchor

Tracks individual anchoring transactions initiated by agents.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | UUID | FK → `agent_configs.id` |
| `receipt_id` | UUID | FK → `receipts.id` (optional) |
| `bundle_hash` | string | 0x-prefixed SHA-256 hash |
| `anchor_txid` | string | On-chain transaction hash (set after send) |
| `chain` | string | Chain name (default: `flare`) |
| `status` | string | `pending` → `confirmed` or `failed` |
| `anchored_at` | datetime | Timestamp of on-chain confirmation |
| `created_at` | datetime | Record creation time |

### AgentConfig (anchoring-relevant fields)

| Column | Type | Description |
|--------|------|-------------|
| `anchor_wallet_address` | string | Dedicated wallet for gas fees |
| `anchor_private_key_encrypted` | string | Encrypted private key for signing |

---

## Execution Modes

### Platform Mode (`execution_mode: "platform"`)

The middleware handles everything:

1. Receipt is created and processed (ISO generation, bundling).
2. The default worker computes the bundle hash and sets status to `awaiting_anchor`.
3. An anchor job is enqueued to the `anchor` Redis queue.
4. The anchor worker signs and sends the transaction using the system wallet (`ANCHOR_PRIVATE_KEY`).
5. The `AnchorPoller` thread monitors the transaction until confirmed.
6. On confirmation, the receipt status is set to `anchored`.

### Tenant Mode (`execution_mode: "tenant"`)

The tenant handles on-chain submission:

1. Receipt is created and processed — status becomes `awaiting_anchor`.
2. The tenant reads the `bundle_hash` from the receipt.
3. The tenant calls `anchorEvidence(bundleHash)` on their own contract using their own wallet and tooling.
4. The tenant calls `POST /v1/iso/confirm-anchor` with the transaction hash.
5. The middleware fetches the transaction receipt from the chain, verifies the `EvidenceAnchored` event log matches the expected bundle hash and contract address, and marks the receipt as `anchored`.

Tenant mode requires `anchoring.chains` to be configured in the project config with at least one entry containing `name` and `contract`.

---

## Anchor Worker Internals

### Transaction Building

The `_build_tx_anchor` function in `app/anchor.py`:

1. Fetches the current nonce for the signing account (with `"pending"` block tag).
2. Reads the chain ID.
3. Attempts EIP-1559 fee estimation (`fee_history` with 5-block window). Falls back to legacy `gas_price` if unavailable.
4. Estimates gas with a 1.2x buffer (fallback: 200,000 gas).
5. Builds the transaction via the contract function's `build_transaction()`.

### Retry Logic

`anchor_bundle()` retries up to 3 times with increasing backoff (1s, 2s, 3s). Each attempt rebuilds the transaction (fresh nonce + gas estimate).

`anchor_send()` is the non-blocking variant used by the worker — it sends the transaction and returns immediately without waiting for confirmation. Confirmation is handled by the `AnchorPoller`.

The `send_raw_transaction` call is wrapped in a thread pool with a configurable hard timeout (`ANCHOR_SEND_TIMEOUT`, default 30s) to prevent indefinite hangs on unresponsive RPC nodes.

### RPC Failover

`_load_web3()` tries the primary RPC (`FLARE_RPC_URL`) with a 2-second connectivity check. If it fails or is slow, it falls back to `FLARE_RPC_URL_FALLBACK` (intended for a local node). If both fail, it returns the primary with a 30-second timeout and lets the caller handle errors.

### AnchorPoller

The poller runs as a daemon thread inside the anchor worker process. Its `_poll_once()` cycle:

1. **Pick up new**: Scans the database for `awaiting_anchor` receipts with a `flare_txid` that aren't already being tracked.
2. **Retry unsent**: Scans for `awaiting_anchor` or `failed` receipts with a `bundle_hash` but no `flare_txid` (send never happened). Re-enqueues them to the anchor queue.
3. **Check confirmations**: For each tracked pending transaction, calls `anchor_confirm()` to check if the transaction receipt exists on-chain.
4. **Finalise or fail**: Confirmed transactions → status `anchored` + `ChainAnchor` record. Timed-out transactions (> `ANCHOR_CONFIRM_TIMEOUT`) → status `failed`.

### Self-Recovery Safeguards

| Safeguard | Description |
|-----------|-------------|
| **Dedup check** | Anchor jobs skip receipts already `anchored` or with an existing `flare_txid` |
| **Per-receipt retry limit** | After 5 consecutive send failures, the receipt is marked `failed` permanently. Counter stored in Redis key `anchor:retries:{receipt_id}` |
| **Queue size cap** | The retry poller stops enqueuing when the anchor queue exceeds 300 jobs |
| **Dedup set** | Redis set `anchor:retry:enqueued` prevents the same receipt from being enqueued twice within 10 minutes |

To manually retry a permanently failed receipt:

```bash
docker compose exec redis redis-cli del anchor:retries:<receipt_id>
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLARE_RPC_URL` | `https://flare-api.flare.network/ext/C/rpc` | Primary RPC endpoint |
| `FLARE_RPC_URL_FALLBACK` | — | Fallback RPC (e.g., local node) |
| `ANCHOR_CONTRACT_ADDR` | `0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8` | EvidenceAnchor contract address |
| `ANCHOR_PRIVATE_KEY` | — | Private key for signing anchor transactions |
| `ANCHOR_ABI_PATH` | `contracts/EvidenceAnchor.abi.json` | Path to contract ABI |
| `ANCHOR_LOOKBACK_BLOCKS` | `50000` | Blocks to search back for events (~14 hours on Flare) |
| `ANCHOR_PUBLIC_BATCH_SIZE` | `10` | Pause after N sends (public RPC) |
| `ANCHOR_LOCAL_BATCH_SIZE` | `50` | Pause after N sends (local/private RPC) |
| `ANCHOR_RETRY_INTERVAL` | `30` | Seconds between retry sweeps for unsent receipts |
| `ANCHOR_POLL_INTERVAL` | `3` | Seconds between confirmation polling cycles |
| `ANCHOR_CONFIRM_TIMEOUT` | `180` | Seconds to wait for tx confirmation before failing |
| `ANCHOR_JOB_TIMEOUT` | `120` | RQ job hard timeout in seconds |
| `ANCHOR_SEND_TIMEOUT` | `30` | Timeout for `send_raw_transaction` RPC calls |
| `WORKERS` | `1` | Number of default worker replicas (receipt processing) |

### Project-Level Config

Set via `PUT /v1/projects/{project_id}/config`:

```json
{
  "anchoring": {
    "execution_mode": "platform",
    "chains": [
      {
        "name": "flare",
        "contract": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
        "rpc_url": "https://flare-api.flare.network/ext/C/rpc",
        "explorer_base_url": "https://flarescan.com"
      }
    ]
  }
}
```

### Agent-Level Config

Set via `PUT /v1/agents/{agent_id}/anchoring-config`:

```json
{
  "auto_anchor_enabled": true,
  "anchor_on_payment": true,
  "anchor_wallet": "0xDedicatedWallet..."
}
```

---

## Verification Flow

Verification works in reverse — given a bundle hash (or a URL from which the hash is computed), the system searches for a matching `EvidenceAnchored` event on-chain.

`find_anchor()` in `app/anchor.py`:

1. Connects to the chain and loads the contract.
2. Gets the latest block number.
3. Fetches logs from `latest - ANCHOR_LOOKBACK_BLOCKS` to `latest` matching the `EvidenceAnchored` event topic.
4. Iterates logs in reverse (most recent first) and decodes the `bundleHash` argument.
5. If a match is found, returns the transaction hash and block timestamp.

For tenant-mode verification (`verify_anchor_tx()`), the logic is different — it fetches the transaction receipt for a specific txid and checks the logs directly, verifying the event was emitted by the expected contract with the expected bundle hash.

---

## Multi-Chain Anchoring

The same bundle hash can be anchored to multiple chains. Each chain is configured in the project's `anchoring.chains` array. In platform mode, the system sends a separate transaction to each configured chain. In tenant mode, the tenant submits a `confirm-anchor` call per chain.

The receipt transitions to `anchored` only after all configured chains are confirmed.

---

## Scaling

The **default worker** (receipt processing) can be safely scaled horizontally:

```bash
WORKERS=5 docker compose up -d
```

The **anchor worker** should run as a single instance because it manages nonces atomically via Redis. Running multiple anchor workers risks nonce collisions unless you have a local RPC node and understand the nonce coordination mechanism.

The `AnchorPoller` runs as a daemon thread inside the anchor worker — it does not need separate scaling.
