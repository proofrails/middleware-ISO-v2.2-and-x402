# Configure Agent Anchoring

This guide covers setting up on-chain anchoring for an agent, including auto-anchor on x402 payment and manual data anchoring.

## Prerequisites

- A running ProofRails backend
- An agent registered via `POST /v1/agents`
- A Flare wallet with enough FLR for gas (anchoring costs ~0.001 FLR per call)

## 1. Register an agent

```bash
curl -X POST /v1/agents \
  -H "X-API-Key: <your_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Payment Agent",
    "wallet_address": "0xAgentWallet"
  }'
# Returns: { "id": "<agent_id>", ... }
```

## 2. Configure anchoring

```bash
curl -X PUT /v1/agents/<agent_id>/anchoring-config \
  -H "X-API-Key: <your_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_anchor_enabled": true,
    "anchor_on_payment": true,
    "anchor_wallet_address": "0xAnchorWallet"
  }'
```

| Field | Description |
|-------|-------------|
| `auto_anchor_enabled` | Anchor agent activity automatically |
| `anchor_on_payment` | Anchor each verified x402 payment |
| `anchor_wallet_address` | Wallet to use for anchor transactions (optional, falls back to `ANCHOR_PRIVATE_KEY` env var) |

## 3. Manually anchor JSON data

```bash
curl -X POST /v1/agents/<agent_id>/anchor-data \
  -H "X-API-Key: <your_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "receipt_id": "abc-123",
      "event": "payment_verified",
      "amount": 100
    },
    "description": "Payment proof",
    "chain": "flare",
    "submit_onchain": true
  }'
```

Response:

```json
{
  "id": "<anchor_id>",
  "agent_id": "<agent_id>",
  "anchor_hash": "0x1a2b3c...",
  "chain": "flare",
  "status": "pending",
  "submit_onchain": true,
  "created_at": "2026-04-30T12:00:00Z"
}
```

The `status` transitions from `pending` → `confirmed` once the transaction is mined. Check with `GET /v1/agents/<agent_id>/anchors`.

## 4. List anchors

```bash
curl /v1/agents/<agent_id>/anchors?days=7 \
  -H "X-API-Key: <your_key>"
```

## 5. Private key configuration

The recommended way to provide a signing key is through the `ANCHOR_PRIVATE_KEY` server environment variable:

```env
ANCHOR_PRIVATE_KEY=0x<hex_private_key>
```

If `anchor_wallet_address` is configured on the agent, the system uses that wallet. If only `ANCHOR_PRIVATE_KEY` is set in environment, it uses that. If neither is configured, anchor tasks will be queued but fail.

**Warning**: Storing a private key in `anchor_private_key_encrypted` via the API is obfuscated with base64, not truly encrypted. Use `ANCHOR_PRIVATE_KEY` for production deployments.

## 6. Verify an anchor

Anyone can verify an anchor without trusting ProofRails:

```bash
# Get the hash and txid from the anchor record
HASH=0x1a2b3c...
TXID=0xdeadbeef...

# Query the Flare anchor contract directly
cast call <ANCHOR_CONTRACT> "verify(bytes32)" $HASH \
  --rpc-url https://flare-api.flare.network/ext/C/rpc
```

## Using the Python SDK

```python
from iso_middleware_sdk import ISOClient

client = ISOClient(base_url="http://localhost:8000", api_key="your_key")

# Configure anchoring
client.update_agent_anchoring_config(
    agent_id,
    auto_anchor_enabled=True,
    anchor_on_payment=True,
)

# Anchor data
result = client.anchor_agent_data(
    agent_id,
    data={"receipt_id": "abc-123", "event": "verified"},
    description="Payment proof",
    chain="flare",
    submit_onchain=True,
)
print(result["anchor_hash"])
```

## See also

- [API: Anchoring](../api/anchoring.md)
- [Agentic Workflows](../concepts/agentic-workflows.md)
- [Known Limitations](../KNOWN_LIMITATIONS.md)
