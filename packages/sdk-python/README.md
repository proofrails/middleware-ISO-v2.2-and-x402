# ISO Middleware SDK (Python)

> **📊 Implementation Status**: See project root [docs/FEATURE_STATUS.md](../../docs/FEATURE_STATUS.md) for comprehensive tracking.

Python client library for the ISO 20022 Middleware Platform.

## Feature Support

| Feature | Status | Notes |
|---------|--------|-------|
| List Receipts | ✅ | With filters and scope |
| Get Receipt | ✅ | Full receipt details |
| Get Anchors | ✅ | Multi-chain anchor list |
| Confirm Anchor | ✅ | Tenant-mode anchoring |
| Verify Bundle | ✅ | URL and hash-based |
| Verify CID | ✅ | IPFS/Arweave support |
| Project Config | ✅ | Get/put per-project |
| Statements | ✅ | camt.052 & camt.053 |
| AI Status | ✅ | Check AI provider |
| Auth Info | ✅ | Get current principal |
| Refund | 🔜 | Being implemented |

## Installation

```bash
pip install iso-middleware-sdk
```

## Quick Start

```python
from iso_middleware_sdk import ISOClient

# Initialize client
client = ISOClient(
    base_url="https://your-middleware-api.com",
    api_key="your_api_key_here"
)

# List receipts
receipts = client.list_receipts(
    status="anchored",
    page=1,
    page_size=20,
    scope="mine"
)

print(f"Found {receipts['total']} receipts")
for receipt in receipts['items']:
    print(f"- {receipt['id']}: {receipt['amount']} {receipt['currency']}")
```

## API Methods

### Receipts
```python
# List receipts with filters
receipts = client.list_receipts(
    status="anchored",
    page=1,
    page_size=20,
    scope="mine"  # or "all" (requires admin)
)

# Get specific receipt
receipt = client.get_receipt("receipt-uuid-here")

# Get per-chain anchor transactions
anchors = client.get_anchors("receipt-uuid-here")
```

### Verification
```python
# Verify bundle by URL
verification = client.verify_bundle(
    bundle_url="https://example.com/bundle.zip"
)

# Verify bundle by hash
verification = client.verify_bundle(
    bundle_hash="0x..."
)

# Verify CID (IPFS/Arweave)
verification = client.verify_cid(
    cid="Qm...",
    store="ipfs",  # or "arweave" or "auto"
    receipt_id="optional-receipt-id"
)
```

### Tenant Anchoring
```python
# Confirm anchor after manual on-chain submission
result = client.confirm_anchor(
    receipt_id="receipt-uuid",
    flare_txid="0x...",
    chain="flare"  # optional, uses default if not specified
)
```

### Project Configuration
```python
# Get project configuration
config = client.get_project_config("project-uuid")

# Update project configuration
client.put_project_config("project-uuid", updated_config)
```

### Statements
```python
# Generate daily statement (camt.053)
statement = client.camt053(date="2026-01-19")

# Generate intraday statement (camt.052)
statement = client.camt052(date="2026-01-19", window="09:00-17:00")
```

### AI & Auth
```python
# Check AI status
ai_status = client.ai_status()
print(f"AI enabled: {ai_status['enabled']}, Provider: {ai_status['provider']}")

# Get current principal information
me = client.auth_me()
print(f"Role: {me['role']}, Is Admin: {me['is_admin']}")
```

### Refunds
```python
# Initiate a refund for an anchored receipt
refund = client.refund(
    original_receipt_id="receipt-uuid",
    reason_code="CUST"  # Optional: CUST, DUPL, TECH, FRAD
)

print(f"Refund receipt ID: {refund['refund_receipt_id']}")
print(f"Status: {refund['status']}")

# Example: Full refund workflow
receipt = client.get_receipt("original-receipt-uuid")
if receipt['status'] == 'anchored':
    refund_result = client.refund(
        original_receipt_id=receipt['id'],
        reason_code="CUST"
    )
    print(f"Refund created: {refund_result['refund_receipt_id']}")
```

## Self-hosted Anchoring (Tenant Mode) ✅

In tenant mode, the middleware generates evidence first (receipt becomes `awaiting_anchor`) and the tenant anchors on-chain.

High-level steps:
1. Configure per-project anchoring chains (`execution_mode='tenant'`, `chains=[{name, contract, rpc_url?}]`).
2. Send the bundle hash to your contract (e.g. `EvidenceAnchor.anchorEvidence(bundle_hash)`) using your own EVM tooling (web3.py, ethers, etc.).
3. Call `confirm_anchor()` to let the platform validate the tx log against the configured contract.

Multi-chain: if you configured multiple chains in `chains[]`, submit a confirm per chain. The receipt becomes `anchored` only once all are confirmed.

### Example with web3.py

```python
from web3 import Web3
from iso_middleware_sdk import ISOClient

# Initialize SDK client
client = ISOClient(
    base_url="https://your-middleware-api.com",
    api_key="your_api_key_here"
)

# Get project configuration to find contract address
config = client.get_project_config("your-project-id")
chain = config['anchoring']['chains'][0]  # First configured chain

# Connect to blockchain
w3 = Web3(Web3.HTTPProvider(chain['rpc_url'] or 'https://rpc.ankr.com/flare'))
contract = w3.eth.contract(
    address=chain['contract'],
    abi=[{
        "type": "function",
        "name": "anchorEvidence",
        "inputs": [{"name": "bundleHash", "type": "bytes32"}],
        "outputs": []
    }]
)

# Get receipt and bundle hash
receipt = client.get_receipt("receipt-uuid")
bundle_hash = receipt['bundle_hash']

# Anchor on-chain
tx = contract.functions.anchorEvidence(
    Web3.to_bytes(hexstr=bundle_hash)
).transact({'from': your_account})

# Wait for confirmation
tx_receipt = w3.eth.wait_for_transaction_receipt(tx)

# Confirm back to middleware
client.confirm_anchor(
    receipt_id=receipt['id'],
    flare_txid=tx.hex(),
    chain=chain['name']
)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

## Contributing

When adding new features:
1. Add the method to `src/iso_middleware_sdk/client.py`
2. Update this README with examples
3. Update [docs/FEATURE_STATUS.md](../../docs/FEATURE_STATUS.md)
4. Add tests if applicable
5. Update type hints

## Error Handling

The SDK raises exceptions for HTTP errors:

```python
from iso_middleware_sdk import ISOClient
from iso_middleware_sdk.exceptions import APIError, AuthenticationError

client = ISOClient(base_url="...", api_key="...")

try:
    receipt = client.get_receipt("invalid-id")
except AuthenticationError:
    print("Invalid API key")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

## License

MIT
