# API: Anchoring

## Receipt anchoring

Receipt anchoring happens automatically when a receipt is created (platform mode) or when `POST /v1/iso/confirm-anchor` is called (tenant mode).

See [API: Verification](./verification.md) for querying anchor status.

## Agent anchoring

Agent anchoring is separate from receipt anchoring. It is used to anchor arbitrary JSON data associated with an agent's activity.

### Hash computation

The anchor hash is computed as:

```
canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
hash = "0x" + sha256(canonical_json.encode("utf-8")).hexdigest()
```

This is deterministic: the same input always produces the same hash.

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v1/agents/{id}/anchoring-config` | Get agent anchoring settings |
| `PUT /v1/agents/{id}/anchoring-config` | Update agent anchoring settings |
| `POST /v1/agents/{id}/anchor-data` | Hash JSON + optional on-chain anchor |
| `POST /v1/agents/{id}/anchor` | Anchor existing bundle hash |
| `GET /v1/agents/{id}/anchors` | List anchor records |
| `GET /v1/agents/{id}/activity-unified` | Payments + anchors merged feed |

### Anchor record statuses

| Status | Meaning |
|--------|---------|
| `pending` | Hash recorded, on-chain submission queued or not requested |
| `confirmed` | Transaction mined, `anchor_txid` set |
| `failed` | On-chain submission failed; check server logs |

### Background anchoring

On-chain anchor submissions run as FastAPI `BackgroundTasks`. The API returns immediately with `status: "pending"`. Poll `GET /v1/agents/{id}/anchors` to check confirmation.

### Anchor contract

The anchor contract address is configured in `ANCHOR_CONTRACT`. The contract must expose a `store(bytes32)` function (or equivalent). The default ProofRails anchor contract is deployed on Flare mainnet and Coston2.

### Signing key priority

1. Agent's `anchor_private_key_encrypted` (decoded from base64)
2. `ANCHOR_PRIVATE_KEY` server environment variable

If neither is configured, `submit_onchain: true` will create a `pending` record that immediately transitions to `failed`.

## See also

- [Configure Agent Anchoring](../guides/configure-agent-anchoring.md)
- [Flare-Native Implementations](../concepts/flare-native-implementations.md)
