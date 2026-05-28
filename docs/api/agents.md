# API: Agents

## CRUD

### Create agent
```
POST /v1/agents
```
Body: `AgentCreate` — `name`, `wallet_address`, optional `xmtp_address`, `pricing_rules`, `project_id`.

### List agents
```
GET /v1/agents
```
Returns agents for the authenticated project.

### Get agent
```
GET /v1/agents/{agent_id}
```

### Update agent
```
PUT /v1/agents/{agent_id}
```
Body: `AgentUpdate` — any subset of `name`, `wallet_address`, `xmtp_address`, `pricing_rules`, `status`.

### Delete agent
```
DELETE /v1/agents/{agent_id}
```

### Update AI config
```
PUT /v1/agents/{agent_id}/ai-config
```
Body: `AgentAIConfigUpdate` — `ai_mode`, `ai_system_prompt`, `ai_provider`, `ai_model`, `ai_api_key`, `ai_endpoint`.

### Test AI parsing
```
POST /v1/agents/{agent_id}/test-ai
```
Body: `{"test_message": "list receipts"}`.

---

## Anchoring

### Get anchoring config
```
GET /v1/agents/{agent_id}/anchoring-config
```
Returns `auto_anchor_enabled`, `anchor_on_payment`, `anchor_wallet`.

### Update anchoring config
```
PUT /v1/agents/{agent_id}/anchoring-config
```
Body: `AgentAnchoringConfig` — `auto_anchor_enabled`, `anchor_on_payment`, `anchor_wallet_address`, optional `anchor_private_key`.

**Security note**: `anchor_private_key` is stored base64-encoded, not encrypted. Prefer setting `ANCHOR_PRIVATE_KEY` in the server environment.

### Hash and anchor JSON data
```
POST /v1/agents/{agent_id}/anchor-data
```
Body:
```json
{
  "data": { "any": "json_object" },
  "description": "optional label",
  "chain": "flare",
  "submit_onchain": false
}
```
Response: `AgentAnchorDataResponse` — `id`, `anchor_hash`, `chain`, `status`, `submit_onchain`, `created_at`.

The `anchor_hash` is SHA-256 of canonical JSON (sorted keys, compact separators), 0x-prefixed.

### Anchor existing bundle hash
```
POST /v1/agents/{agent_id}/anchor
```
Body: `AgentAnchorRequest` — `bundle_hash`, optional `receipt_id`. Use when you already have a hash.

### List anchors
```
GET /v1/agents/{agent_id}/anchors?days=7&status=confirmed
```

### Unified activity feed
```
GET /v1/agents/{agent_id}/activity-unified?days=7
```
Returns interleaved payments and anchors sorted by timestamp.

---

## x402 analytics

### List payments
```
GET /v1/x402/payments?limit=50
```
Auth required.

### Revenue summary
```
GET /v1/x402/revenue?days=7
```
Admin only.
