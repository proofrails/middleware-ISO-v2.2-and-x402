# ISO Middleware SDK (Python)

Python client for the ProofRails API.

## Installation

```bash
pip install -e packages/sdk-python   # from repo root
# or
pip install iso-middleware-sdk       # once published
```

## Quick start

```python
from iso_middleware_sdk import ISOClient

client = ISOClient(
    base_url="http://localhost:8000",
    api_key="your_api_key",
)

page = client.list_receipts(scope="mine", page=1, page_size=20)
print(f"{page['total']} receipts")
for r in page["items"]:
    print(r["id"], r["status"], r["amount"], r["currency"])
```

## API methods

### Receipts

```python
# List receipts (paginated)
page = client.list_receipts(
    status="anchored",
    chain="flare",
    scope="mine",    # or "all" (admin only)
    page=1,
    page_size=20,
)
# page: { items, total, page, page_size }

# Get one receipt
receipt = client.get_receipt("receipt-uuid")

# Lightweight status poll
status = client.get_receipt_status("receipt-uuid")

# Per-chain anchor txids
anchors = client.get_anchors("receipt-uuid")
```

### Verification

```python
client.verify_bundle(bundle_url="https://...")
client.verify_bundle(bundle_hash="0x...")
client.verify_cid(cid="Qm...", store="ipfs", receipt_id="optional")
```

### Statements

```python
daily = client.camt053(date="2026-01-19")
intraday = client.camt052(date="2026-01-19", window="09:00-17:00")
```

### Refunds

```python
refund = client.refund(
    original_receipt_id="receipt-uuid",
    reason_code="CUST",  # CUST | DUPL | TECH | FRAD
)
# refund: { refund_receipt_id, status }
```

### Tenant anchoring

```python
client.confirm_anchor(
    receipt_id="receipt-uuid",
    flare_txid="0x...",
    chain="flare",
)
```

### Project configuration

```python
config = client.get_project_config("project-uuid")
client.put_project_config("project-uuid", {
    "anchoring": {
        "execution_mode": "platform",  # or "tenant"
        "chains": [{"name": "flare", "contract": "0x...", "rpc_url": "..."}],
    }
})
```

### Agent CRUD

```python
agent = client.create_agent(
    name="My Agent",
    wallet_address="0x...",
    xmtp_address="0x...",
)

agents = client.list_agents()
agent = client.get_agent("agent-uuid")
client.update_agent("agent-uuid", name="Renamed")
client.delete_agent("agent-uuid")
```

### Agent anchoring config

```python
config = client.get_agent_anchoring_config("agent-uuid")

client.update_agent_anchoring_config(
    "agent-uuid",
    auto_anchor_enabled=True,
    anchor_on_payment=False,
    anchor_wallet_address="0x...",
)
```

### Agent anchor data

```python
# Hash arbitrary JSON and optionally submit on-chain
result = client.anchor_agent_data(
    agent_id="agent-uuid",
    data={"invoice_id": "INV-001", "amount": "100.00"},
    description="Invoice proof",
    chain="flare",           # flare | coston2 | base | sepolia
    submit_onchain=True,
)
# result: { id, agent_id, anchor_hash, chain, status, submit_onchain }

# List recent anchor records
records = client.list_agent_anchors("agent-uuid", days=7)
```

### x402 analytics

```python
payments = client.list_x402_payments(limit=50)
revenue = client.get_x402_revenue(days=7)
# revenue: { total_revenue, payment_count, days, by_endpoint }
```

### Misc

```python
ai = client.ai_status()
me = client.auth_me()
```

## Tenant anchoring — full example

```python
from web3 import Web3
from iso_middleware_sdk import ISOClient

client = ISOClient(base_url="http://localhost:8000", api_key="...")

# Get bundle hash
receipt = client.get_receipt("receipt-uuid")

# Anchor on-chain
w3 = Web3(Web3.HTTPProvider("https://flare-api.flare.network/ext/C/rpc"))
contract = w3.eth.contract(
    address="0x<anchor-contract>",
    abi=[{
        "type": "function",
        "name": "anchorEvidence",
        "inputs": [{"name": "bundleHash", "type": "bytes32"}],
        "outputs": [],
    }],
)
tx = contract.functions.anchorEvidence(
    Web3.to_bytes(hexstr=receipt["bundle_hash"])
).transact({"from": your_account})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx)

# Confirm to middleware
client.confirm_anchor(
    receipt_id=receipt["id"],
    flare_txid=tx.hex(),
    chain="flare",
)
```

## Error handling

```python
from iso_middleware_sdk import ISOClient
import requests

client = ISOClient(base_url="...", api_key="...")

try:
    receipt = client.get_receipt("invalid-id")
except requests.HTTPError as e:
    print(e.response.status_code, e.response.text)
```

## Development

```bash
pip install -e ".[dev]"
pytest
black src/
ruff check src/
```

## License

MIT
