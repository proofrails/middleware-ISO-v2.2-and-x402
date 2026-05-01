# Agentic Workflows

ProofRails v2.2 adds a first-class agent layer. Agents are autonomous programs — or AI assistants — that interact with the ProofRails API programmatically, pay for premium access using x402, and generate evidence for their activity.

## Agent registration

An agent is registered in ProofRails with:

- `name` — human-readable label
- `wallet_address` — the EVM address that sends x402 payments
- `xmtp_address` (optional) — XMTP identity for messaging-based agents
- `pricing_rules` — per-operation price overrides
- `ai_mode` — `simple` (pattern matching), `shared` (platform AI), or `custom` (BYO model)
- `project_id` — owning project for access control

Agents are managed via `POST/GET/PUT/DELETE /v1/agents`.

## XMTP agent

The reference XMTP agent (`agents/iso-x402-agent/`) listens for XMTP messages and supports these commands:

| Command | Description |
|---------|-------------|
| `help` | List available commands |
| `list [n]` | List recent receipts |
| `get <receipt_id>` | Get receipt details |
| `verify <bundle_url>` | Verify an evidence bundle |
| `statement <date>` | Generate a camt.053 statement |
| `refund <receipt_id>` | Initiate a refund |
| `status <receipt_id>` | Lightweight status check |
| `anchor <json>` | Hash JSON data and anchor on-chain |
| `list anchors [days]` | List recent anchor records |
| `verify anchor <hash>` | Check whether a hash is confirmed |

Commands that access premium endpoints (`verify`, `statement`, `refund`, `anchor`) automatically send a USDC micropayment before making the API call.

## Anchoring

Agents can anchor arbitrary JSON data to Flare. The data is hashed (SHA-256 of canonical JSON), and only the hash is recorded on-chain. This creates an immutable, verifiable record that the data existed at a given time.

Configure anchoring per agent:

```
PUT /v1/agents/{agent_id}/anchoring-config
{
  "auto_anchor_enabled": true,
  "anchor_on_payment": true,
  "anchor_wallet_address": "0x..."
}
```

Submit data for anchoring:

```
POST /v1/agents/{agent_id}/anchor-data
{
  "data": { "receipt_id": "...", "amount": 100 },
  "description": "Payment proof",
  "chain": "flare",
  "submit_onchain": true
}
```

## Private key handling

The anchoring wallet private key is stored base64-encoded in the database. This is obfuscated, not encrypted. For production deployments:

- Set `ANCHOR_PRIVATE_KEY` as a server environment variable instead.
- Restrict DB access appropriately.
- Do not use wallets with significant funds for anchoring.

This is documented as a known limitation. See [Known Limitations](../KNOWN_LIMITATIONS.md).

## See also

- [Configure Agent Anchoring](../guides/configure-agent-anchoring.md)
- [Deploy XMTP Agent](../guides/deploy-xmtp-agent.md)
- [API: Agents](../api/agents.md)
- [API: Anchoring](../api/anchoring.md)
