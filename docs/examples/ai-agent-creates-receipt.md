# Example: AI Agent Creates a Receipt

This example shows an XMTP agent workflow: a user sends a message to the agent, the agent lists recent receipts, and the user asks for a specific receipt to be anchored.

## Prerequisites

- XMTP agent running (see [Deploy XMTP Agent](../guides/deploy-xmtp-agent.md))
- Agent has an `AGENT_ID` registered in ProofRails
- Anchoring wallet configured

## Conversation flow

```
User → agent XMTP address:

  "list"

Agent response:
  📋 Recent Receipts (5 of 47):

  🧾 invoice-2026-001
     ID: `3fa85f64-5717-4562-b3fc-2c963f66afa6`
     Amount: 100.0 FLR
     Status: anchored
     Created: 4/30/2026, 12:00:00 PM

  ...


User:
  "status 3fa85f64-5717-4562-b3fc-2c963f66afa6"

Agent response:
  Receipt: 3fa85f64-5717-4562-b3fc-2c963f66afa6
  Status:  anchored
  Bundle:  0x1a2b3c...
  Anchor:  0xdeadbeef...
  Anchored at: 2026-04-30T12:00:07Z


User:
  "anchor {"receipt_id": "3fa85f64", "event": "user_verified", "user": "alice"}"

Agent response:
  Anchor queued.
  Hash:   0x9f8e7d...
  Chain:  flare
  Status: pending
  ID:     a1b2c3d4-...


User (30 seconds later):
  "list anchors"

Agent response:
  Anchors (last 7 day(s)):

  1. 0x9f8e7d…
     Chain: flare  Status: confirmed
     Tx:    0xdeadcafe...
     Created: 2026-04-30T12:05:00Z
```

## What happened under the hood

1. `list` → `GET /v1/receipts` → paginated response, items rendered as text.
2. `status <id>` → `GET /v1/iso/receipts/<id>/status` → lightweight status check.
3. `anchor <json>` → `POST /v1/agents/<agent_id>/anchor-data` with `submit_onchain: true` → background task anchors on Flare.
4. `list anchors` → `GET /v1/agents/<agent_id>/anchors` → rendered as numbered list.

## Programmatic equivalent (Python SDK)

```python
from iso_middleware_sdk import ISOClient

client = ISOClient(base_url="http://localhost:8000", api_key="your_key")

# Step 1: List receipts
page = client.list_receipts(page_size=5)
for r in page["items"]:
    print(r["reference"], r["status"])

# Step 2: Status
status = client.get_receipt_status(receipt_id)
print(status)

# Step 3: Anchor data
result = client.anchor_agent_data(
    agent_id=agent_id,
    data={"receipt_id": receipt_id, "event": "user_verified"},
    description="User verification",
    chain="flare",
    submit_onchain=True,
)
print(result["anchor_hash"])

# Step 4: List anchors
anchors = client.list_agent_anchors(agent_id, days=7)
for a in anchors:
    print(a["bundle_hash"], a["status"])
```
