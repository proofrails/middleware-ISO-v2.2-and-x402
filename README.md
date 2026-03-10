# ISO 20022 Payments Middleware with x402 & Agent Anchoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

> **Production-ready middleware for ISO 20022 payment processing with blockchain anchoring, x402 micropayments, and autonomous AI agents**

Transform blockchain transactions into compliant ISO 20022 XML messages with cryptographic evidence bundles anchored on EVM chains. Enable pay-per-use API access with USDC micropayments and deploy autonomous XMTP agents.

**[Quick Start](#quick-start)** | **[Core Features](#core-features)** | **[Projects](#project-management)** | **[Receipts](#receipt-verification)** | **[Dashboard](#dashboard--ui)** | **[API](#api-reference)** | **[SDK](#sdk-usage)** | **[Agents](#ai-agent-integration)**

---

## Overview

The ISO 20022 Middleware provides a complete solution for payment processing:

### 🎯 Core Capabilities

- **15 ISO 20022 Message Types**: pain.001, pain.002, pain.007, pain.008, pacs.002, pacs.004, pacs.007, pacs.008, pacs.009, camt.029, camt.052, camt.053, camt.054, camt.056, remt.001
- **Multi-Chain Anchoring**: Evidence bundles anchored on Ethereum, Base, Flare, Optimism
- **Project Isolation**: Multi-tenant support with Sign-In With Ethereum (SIWE) authentication
- **Evidence Bundles**: Deterministic ZIP files with cryptographic signatures
- **Real-Time Updates**: Server-Sent Events (SSE) for live receipt tracking
- **TypeScript & Python SDKs**: Full-featured client libraries with contract ABIs

### 💰 x402 Payment Protocol

- **Micropayment API**: Pay-per-use endpoints with USDC on Base chain
- **6 Premium Endpoints**: Verify bundles, generate statements, FX lookup, bulk operations
- **Automatic Payments**: Transparent USDC handling via x402 protocol
- **Revenue Analytics**: Track payments, usage, and revenue by endpoint

### 🤖 Autonomous Agents

- **XMTP Agent**: Natural language command processing via messaging
- **Agent Management**: Full CRUD API + UI for managing autonomous agents
- **Multi-Agent Support**: Run multiple agents per project with independent wallets
- **Agent Anchoring**: Automatic or manual blockchain anchoring for agents

---

## Core Features
# ISO 20022 Payments Middleware with x402 & Agent Anchoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

> **Production-ready middleware for ISO 20022 payment processing with blockchain anchoring, x402 micropayments, and autonomous AI agents**

Transform blockchain transactions into compliant ISO 20022 XML messages with cryptographic evidence bundles anchored on EVM chains. Enable pay-per-use API access with USDC micropayments and deploy autonomous XMTP agents.

**[Quick Start](#quick-start)** | **[Core Features](#core-features)** | **[Projects](#project-management)** | **[Receipts](#receipt-verification)** | **[Dashboard](#dashboard--ui)** | **[API](#api-reference)** | **[SDK](#sdk-usage)** | **[Agents](#ai-agent-integration)**

---

## Overview

The ISO 20022 Middleware provides a complete solution for payment processing:

### 🎯 Core Capabilities

- **15 ISO 20022 Message Types**: pain.001, pain.002, pain.007, pain.008, pacs.002, pacs.004, pacs.007, pacs.008, pacs.009, camt.029, camt.052, camt.053, camt.054, camt.056, remt.001
- **Multi-Chain Anchoring**: Evidence bundles anchored on Ethereum, Base, Flare, Optimism
- **Project Isolation**: Multi-tenant support with Sign-In With Ethereum (SIWE) authentication
- **Evidence Bundles**: Deterministic ZIP files with cryptographic signatures
- **Real-Time Updates**: Server-Sent Events (SSE) for live receipt tracking
- **TypeScript & Python SDKs**: Full-featured client libraries with contract ABIs

### 💰 x402 Payment Protocol

- **Micropayment API**: Pay-per-use endpoints with USDC on Base chain
- **6 Premium Endpoints**: Verify bundles, generate statements, FX lookup, bulk operations
- **Automatic Payments**: Transparent USDC handling via x402 protocol
- **Revenue Analytics**: Track payments, usage, and revenue by endpoint

### 🤖 Autonomous Agents

- **XMTP Agent**: Natural language command processing via messaging
- **Agent Management**: Full CRUD API + UI for managing autonomous agents
- **Multi-Agent Support**: Run multiple agents per project with independent wallets
- **Agent Anchoring**: Automatic or manual blockchain anchoring for agents

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/alfre97x/middleware-ISO-and-x402.git
cd middleware-ISO-and-x402

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# In a new terminal, start UI
cd web-alt
npm install
npm run dev
```

Access the dashboard at: **http://localhost:3000**

---

## Core Features

### 1. Project Management

Create isolated projects for multi-tenant deployments with independent configurations.

#### Using the UI

1. **Navigate to**: `http://localhost:3000`
2. **Connect Wallet**: Click "Connect Wallet" → Sign with MetaMask
3. **Create Project**:
   - Enter project name
   - Click "Create Project"
   - Project becomes active automatically

4. **Configure Project**:
   - Go to "Settings" tab
   - Set anchoring preferences:
     - **Platform Mode**: Middleware handles anchoring
     - **Tenant Mode**: You handle anchoring with your wallet
   - Save configuration

#### Using the SDK

```typescript
import IsoMiddlewareClient from 'iso-middleware-sdk';

const client = new IsoMiddlewareClient({ 
  baseUrl: 'http://localhost:8000' 
});

// Create project (requires SIWE authentication)
const project = await client.createProject({
  name: 'My Payment Project',
  config: {
    anchoring: {
      execution_mode: 'platform', // or 'tenant'
      chains: [
        { name: 'flare', contract: '0x...', rpc_url: 'https://...' }
      ]
    }
  }
});

// Get project details
const details = await client.getProjectConfig(project.id);
```

#### Using the API

```bash
# Create project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <siwe_token>" \
  -d '{
    "name": "My Project",
    "config": {
      "anchoring": {
        "execution_mode": "platform"
      }
    }
  }'

# List projects
curl http://localhost:8000/v1/projects \
  -H "Authorization: Bearer <siwe_token>"

# Get project config
curl http://localhost:8000/v1/projects/{project_id}/config \
  -H "Authorization: Bearer <siwe_token>"
```

---

### 2. Receipt Generation & Verification

Generate ISO 20022 receipts from blockchain transactions and verify evidence bundles.

#### Record a Transaction (Create Receipt)

**Using the UI:**
1. Navigate to **Home** (http://localhost:3000)
2. Scroll to "Record Transaction" section
3. Fill in details:
   - Transaction hash
   - Chain (flare, ethereum, base, etc.)
   - Amount & currency
   - Sender/receiver wallets
   - Reference ID
4. Click "Record Transaction"
5. View real-time status updates

**Using the SDK:**

```typescript
import IsoMiddlewareClient from 'iso-middleware-sdk';

const client = new IsoMiddlewareClient({ baseUrl: 'http://localhost:8000' });

// Record a tip transaction
const receipt = await client.recordTip({
  tip_tx_hash: '0xabc123...',
  chain: 'flare',
  amount: '100.50',
  currency: 'FLR',
  sender_wallet: '0xSender...',
  receiver_wallet: '0xReceiver...',
  reference: 'invoice-2026-001'
});

console.log('Receipt ID:', receipt.receipt_id);
console.log('Status:', receipt.status);
// Output: Status: pending → bundling → anchored
```

**Using the API:**

```bash
curl -X POST http://localhost:8000/v1/iso/record-tip \
  -H "Content-Type: application/json" \
  -d '{
    "tip_tx_hash": "0xabc123...",
    "chain": "flare",
    "amount": "100.50",
    "currency": "FLR",
    "sender_wallet": "0xSender...",
    "receiver_wallet": "0xReceiver...",
    "reference": "invoice-2026-001"
  }'
```

#### Verify Evidence Bundle

**Using the UI:**
1. Navigate to **Operations** tab
2. Click "Verify Bundle"
3. Enter bundle URL or upload ZIP file
4. View verification results:
   - Bundle integrity
   - Blockchain confirmations
   - ISO message validation

**Using the SDK:**

```typescript
// Verify by URL
const result = await client.verifyBundle({
  bundle_url: 'https://ipfs.io/ipfs/Qm...'
});

// Verify by hash
const result = await client.verifyBundle({
  bundle_hash: '0x1234...'
});

console.log('Valid:', result.valid);
console.log('Chains:', result.chains);
console.log('Messages:', result.iso_messages);
```

**Using the API:**

```bash
curl -X POST http://localhost:8000/v1/iso/verify \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_url": "https://ipfs.io/ipfs/Qm..."
  }'
```

#### List & View Receipts

**Using the UI:**
1. Navigate to **Home** tab
2. View receipts table with:
   - Reference ID
   - Amount & currency
   - Status (pending/bundling/anchored)
   - Created date
3. Click on receipt to view details
4. Download evidence bundle or ISO messages

**Using the SDK:**

```typescript
// List receipts with pagination
const page = await client.listReceipts({
  page: 1,
  page_size: 20,
  scope: 'mine' // or 'all' for admin
});

console.log('Total:', page.total);
page.receipts.forEach(r => {
  console.log(`${r.reference}: ${r.amount} ${r.currency} - ${r.status}`);
});

// Get specific receipt
const receipt = await client.getReceipt('receipt-id');
console.log('Bundle URL:', receipt.bundle_url);
console.log('ISO Messages:', receipt.iso_messages);
```

---

### 3. Dashboard & UI

Full-featured Next.js dashboard for managing all operations.

#### Main Pages

**1. Home (`/`)**
- Recent receipts table
- Quick stats
- Record new transaction
- Real-time status updates via SSE

**2. Operations (`/operations`)**
- Verify evidence bundles
- Generate statements
- Bulk operations
- FX rate lookups

**3. Settings (`/settings`)**
- Project configuration
- API key management
- Anchoring settings
- Network configuration

**4. Agents (`/agents`)**
- Create/manage XMTP agents
- Configure AI settings
- Set up automatic anchoring
- View agent analytics

#### Using the Dashboard

**Connect Wallet:**
1. Click "Connect Wallet" (top-right)
2. Sign message with MetaMask
3. Session persists in httpOnly cookie

**Create Receipt:**
1. Go to Home page
2. Fill transaction details
3. Click "Record Transaction"
4. Watch live updates (no polling needed)

**Verify Bundle:**
1. Go to Operations → Verify
2. Paste bundle URL or upload ZIP
3. View detailed validation results

**Manage Projects:**
1. Click project dropdown (top-right)
2. Select or create project
3. Configure in Settings tab

---

### 4. Agent Anchoring

Agent Anchoring allows AI agents to automatically or manually anchor payment data to the blockchain, creating cryptographically verifiable audit trails. This is particularly useful for:

- ✅ **Compliance**: Immutable records for regulatory requirements
- ✅ **Trust**: Cryptographic proof of payment processing
- ✅ **Automation**: x402 payment-triggered anchoring
- ✅ **Transparency**: Public blockchain verification

### Key Features

- 🔐 **Automatic Anchoring**: Trigger on payment events or manual commands
- ⛓️ **Multi-Chain Support**: Ethereum, Base, Optimism, Flare, and custom EVM chains
- 🤖 **AI Agent Integration**: XMTP agents with natural language commands
- 📊 **Full UI Dashboard**: Web interface for configuration and monitoring
- 🛠️ **SDKs**: TypeScript and Python client libraries
- 💰 **x402 Integration**: Automatic anchoring on micropayments

---

## Quick Start

Choose your preferred method:

### 🖥️ Option 1: Web UI (60 seconds)

```bash
# 1. Start the middleware
uvicorn app.main:app --port 8000

# 2. Start the UI
cd web-alt && npm run dev

# 3. Open browser
open http://localhost:3000/agents
```

**Result**: Configure anchoring with toggles and buttons

### 💻 Option 2: SDK (5 lines of code)

```typescript
import IsoMiddlewareClient from 'iso-middleware-sdk';

const client = new IsoMiddlewareClient({ baseUrl: 'http://localhost:8000' });
await client.updateAgentAnchoringConfig('agent-id', {
  auto_anchor_enabled: true,
  anchor_on_payment: true
});
```

**Result**: Anchoring enabled programmatically

### 🤖 Option 3: AI Agent (Auto-anchor on payments)

```bash
# 1. Configure agent
cd agents/iso-x402-agent
cp .env.example .env
# Set: ANCHOR_ENABLED=true, ANCHOR_ON_PAYMENT=true

# 2. Deploy
npm install && npm start
```

**Result**: Agent auto-anchors on every x402 payment

---

## UI Usage

### Prerequisites

Before starting, ensure:
- ✅ Middleware API running at `http://localhost:8000`
- ✅ Web UI running at `http://localhost:3000`
- ✅ At least one agent configured

### Complete Step-by-Step Guide

#### Step 1: Navigate to Agents Page

1. **Open your browser** to: `http://localhost:3000/agents`

2. **Expected view:**
   ```
   ┌─────────────────────────────────────────┐
   │ ISO Middleware - Agents                 │
   ├─────────────┬───────────────────────────┤
   │ Left Panel  │ Right Panel               │
   │             │                           │
   │ [+ New      │ (Agent details will       │
   │    Agent]   │  appear here)             │
   │             │                           │
   │ Agent List: │                           │
   │ • My Agent  │                           │
   │ • Bot 2     │                           │
   └─────────────┴───────────────────────────┘
   ```

3. **If no agents exist:**
   - Click blue **"New Agent"** button (top-left corner)
   - Fill in: Name, Wallet Address
   - Click **"Create Agent"**

#### Step 2: Select Your Agent

1. **Click on agent name** in left sidebar (e.g., "My Agent")

2. **Right panel opens** showing agent details

3. **Tabs visible:**
   ```
   [Details] [AI Settings] [Activity] [Analytics] [Anchoring] [Pricing] [Revenue]
                                                      ↑
                                           (Click this tab)
   ```

4. **Click the "Anchoring" tab** (⚓ icon, 5th from left)

5. **Wait for panel to load** (~500ms)

#### Step 3: Configure Automatic Anchoring

1. **Locate the configuration panel** at the top:
   ```
   ┌─────────────────────────────────────────┐
   │ Anchoring Configuration                 │
   ├─────────────────────────────────────────┤
   │                                         │
   │ [○] Enable Automatic Anchoring          │
   │                                         │
   │ [○] Anchor on x402 Payment              │
   │                                         │
   │ Anchor Wallet (optional)                │
   │ [_________________________________]     │
   │                                         │
   │             [Save Configuration]        │
   └─────────────────────────────────────────┘
   ```

2. **Enable auto-anchoring:**
   - Click the **first toggle**: "Enable Automatic Anchoring"
   - Toggle switches from `○` gray (off) to `●` blue (on)
   - Text changes: "Disabled" → "Enabled"

3. **Enable payment-triggered anchoring (optional):**
   - Click the **second toggle**: "Anchor on x402 Payment"
   - When enabled, every x402 payment will trigger an anchor

4. **Set dedicated wallet (optional):**
   - Click in the **"Anchor Wallet"** text field
   - Paste your Ethereum address: `0x1234567890123456789012345678901234567890`
   - This wallet will pay gas fees for anchoring

5. **Save your configuration:**
   - Click blue **"Save Configuration"** button
   - Wait for success message: ✅ "Configuration saved successfully!"

#### Step 4: Manual Data Anchoring

1. **Scroll down** to "Manual Anchoring" section:
   ```
   ┌─────────────────────────────────────────┐
   │ Manual Anchoring                        │
   ├─────────────────────────────────────────┤
   │ Data to Anchor (JSON)                   │
   │ ┌─────────────────────────────────────┐ │
   │ │ {                                   │ │
   │ │   "payment_id": "pay-001",          │ │
   │ │   "amount": 100.50                  │ │
   │ │ }                                   │ │
   │ └─────────────────────────────────────┘ │
   │                                         │
   │ Description                             │
   │ [_________________________________]     │
   │                                         │
   │           [Anchor Data]                 │
   └─────────────────────────────────────────┘
   ```

2. **Enter JSON data:**
   - Click in the **JSON editor** field
   - Type or paste your data (must be valid JSON):
     ```json
     {
       "payment_id": "pay-001",
       "amount": 100.50,
       "currency": "USD",
       "timestamp": "2026-01-20T20:00:00Z"
     }
     ```

3. **Add description:**
   - Click in **"Description"** field
   - Type: `Payment verification for order #001`

4. **Submit anchoring:**
   - Click green **"Anchor Data"** button
   - Wait for confirmation: ✅ "Data anchored successfully!"

5. **View the created anchor:**
   - New row appears in "Anchor History" table below
   - Shows: Timestamp, Hash, Status

#### Step 5: View Anchor History

1. **Locate the history table:**
   ```
   ┌────────────────────────────────────────────────────────────────┐
   │ Anchor History                                                 │
   ├──────────────┬─────────────┬────────────┬──────────┬──────────┤
   │ Timestamp    │ Data Hash   │ TX Hash    │ Contract │ Status   │
   ├──────────────┼─────────────┼────────────┼──────────┼──────────┤
   │ 1/20 8:30 PM │ 0x1234...   │ 0xabcd...  │ 0x5678.. │ ✅ Conf. │
   │ 1/20 8:25 PM │ 0x2345...   │ 0xbcde...  │ 0x5678.. │ ⏳ Pend. │
   └──────────────┴─────────────┴────────────┴──────────┴──────────┘
   ```

2. **Understanding the columns:**
   - **Timestamp**: When anchor was created (local time)
   - **Data Hash**: SHA-256 of anchored data (click to copy)
   - **TX Hash**: Blockchain transaction (click to view on Etherscan)
   - **Contract**: Anchor contract address
   - **Status**:
     - ✅ **Confirmed**: On-chain and verified
     - ⏳ **Pending**: Submitted, waiting for confirmation
     - ❌ **Failed**: Error occurred (hover for details)

3. **Copy data hash:**
   - Click the **hash** (e.g., `0x1234...`)
   - Hash copied to clipboard
   - Use for verification or reference

4. **View on blockchain:**
   - Click **TX Hash** link
   - Opens Etherscan in new tab
   - Shows full transaction details

### Troubleshooting UI Issues

#### Issue: Anchoring tab not visible

**Symptoms**: Only 6 tabs visible, no "Anchoring" tab

**Solution**:
1. Refresh the page (Ctrl+R / Cmd+R)
2. Clear browser cache
3. Check browser console for errors (F12)
4. Verify API is running: `curl http://localhost:8000/health`

#### Issue: "Save Configuration" fails

**Symptoms**: Error message or no response

**Solution**:
1. Check browser console (F12) for error details
2. Verify agent ID is correct
3. Check API logs for errors:
   ```bash
   # Check last 50 lines of API logs
   tail -f -n 50 api.log
   ```
4. Ensure database is accessible

#### Issue: Manual anchoring fails

**Symptoms**: Error: "Invalid JSON" or "Anchoring failed"

**Solution**:
1. **Validate JSON**: Use [JSONLint](https://jsonlint.com/)
2. **Check format**: Must be valid JSON object `{...}`
3. **Remove comments**: JSON doesn't support `//` comments
4. **Check wallet balance**: Ensure anchor wallet has ETH for gas

---

## SDK Usage

### TypeScript/JavaScript

#### Installation

```bash
npm install iso-middleware-sdk
```

#### Complete Working Example

```typescript
import IsoMiddlewareClient from 'iso-middleware-sdk';

// Initialize client
const client = new IsoMiddlewareClient({
  baseUrl: 'http://localhost:8000',
  apiKey: process.env.ISO_MW_API_KEY // Optional
});

// 1. Get current anchoring configuration
async function getConfig(agentId: string) {
  const config = await client.getAgentAnchoringConfig(agentId);
  console.log('Current configuration:', config);
  
  // Expected output:
  // {
  //   auto_anchor_enabled: false,
  //   anchor_on_payment: false,
  //   anchor_wallet: null
  // }
  
  return config;
}

// 2. Enable automatic anchoring
async function enableAnchoring(agentId: string) {
  const updated = await client.updateAgentAnchoringConfig(agentId, {
    auto_anchor_enabled: true,
    anchor_on_payment: true,
    anchor_wallet: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'
  });
  
  console.log('✅ Anchoring enabled!', updated);
  
  // Expected output:
  // {
  //   auto_anchor_enabled: true,
  //   anchor_on_payment: true,
  //   anchor_wallet: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'
  // }
}

// 3. Manually anchor data
async function anchorData(agentId: string) {
  const anchor = await client.anchorAgentData(agentId, {
    data: {
      payment_id: 'pay-001',
      amount: 100.50,
      currency: 'USD',
      debtor: 'John Doe',
      creditor: 'Jane Smith'
    },
    description: 'Payment verification for order #001'
  });
  
  console.log('✅ Data anchored!');
  console.log('Anchor ID:', anchor.id);
  console.log('Hash:', anchor.anchor_hash);
  console.log('Status:', anchor.status);
  
  // Expected output:
  // Anchor ID: 550e8400-e29b-41d4-a716-446655440000
  // Hash: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
  // Status: pending
  
  return anchor;
}

// 4. List all anchors for an agent
async function listAnchors(agentId: string) {
  const anchors = await client.listAgentAnchors(agentId);
  
  console.log(`Found ${anchors.length} anchors:`);
  anchors.forEach((anchor, index) => {
    console.log(`\n${index + 1}. Anchor ${anchor.id}`);
    console.log(`   Hash: ${anchor.anchor_hash}`);
    console.log(`   Status: ${anchor.status}`);
    console.log(`   Created: ${anchor.created_at}`);
    if (anchor.anchor_tx_hash) {
      console.log(`   TX: ${anchor.anchor_tx_hash}`);
    }
  });
  
  // Expected output:
  // Found 3 anchors:
  // 
  // 1. Anchor 550e8400-...
  //    Hash: 0x1234...
  //    Status: confirmed
  //    Created: 2026-01-20T20:00:00Z
  //    TX: 0xabcd...
  // ...
}

// 5. Complete workflow
async function main() {
  const agentId = 'agent-550e8400-e29b-41d4-a716-446655440000';
  
  // Get current config
  await getConfig(agentId);
  
  // Enable anchoring
  await enableAnchoring(agentId);
  
  // Anchor some data
  await anchorData(agentId);
  
  // List all anchors
  await listAnchors(agentId);
}

main().catch(console.error);
```

#### Error Handling

```typescript
import IsoMiddlewareClient from 'iso-middleware-sdk';

const client = new IsoMiddlewareClient({
  baseUrl: 'http://localhost:8000',
  apiKey: process.env.ISO_MW_API_KEY
});

async function anchorWithErrorHandling(agentId: string, data: any) {
  try {
    const anchor = await client.anchorAgentData(agentId, {
      data: data,
      description: 'Payment verification'
    });
    
    console.log('✅ Success:', anchor.id);
    return anchor;
    
  } catch (error: any) {
    // Handle specific error cases
    if (error.status === 404) {
      console.error('❌ Agent not found:', agentId);
    } else if (error.status === 422) {
      console.error('❌ Invalid data format:', error.message);
    } else if (error.status === 500) {
      console.error('❌ Server error:', error.message);
    } else {
      console.error('❌ Unknown error:', error);
    }
    
    throw error;
  }
}
```

### Python

#### Installation

```bash
pip install iso-middleware-sdk
```

#### Complete Working Example

```python
from iso_middleware_sdk import Client
import os
from datetime import datetime

# Initialize client
client = Client(
    base_url='http://localhost:8000',
    api_key=os.getenv('ISO_MW_API_KEY')  # Optional
)

# 1. Get current anchoring configuration
def get_config(agent_id: str):
    config = client.get_agent_anchoring_config(agent_id)
    print('Current configuration:', config)
    
    # Expected output:
    # {
    #   'auto_anchor_enabled': False,
    #   'anchor_on_payment': False,
    #   'anchor_wallet': None
    # }
    
    return config

# 2. Enable automatic anchoring
def enable_anchoring(agent_id: str):
    updated = client.update_agent_anchoring_config(
        agent_id=agent_id,
        auto_anchor_enabled=True,
        anchor_on_payment=True,
        anchor_wallet='0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'
    )
    
    print('✅ Anchoring enabled!', updated)
    return updated

# 3. Manually anchor data
def anchor_data(agent_id: str):
    anchor = client.anchor_agent_data(
        agent_id=agent_id,
        data={
            'payment_id': 'pay-001',
            'amount': 100.50,
            'currency': 'USD',
            'debtor': 'John Doe',
            'creditor': 'Jane Smith',
            'timestamp': datetime.utcnow().isoformat()
        },
        description='Payment verification for order #001'
    )
    
    print('✅ Data anchored!')
    print(f'Anchor ID: {anchor["id"]}')
    print(f'Hash: {anchor["anchor_hash"]}')
    print(f'Status: {anchor["status"]}')
    
    return anchor

# 4. List all anchors for an agent
def list_anchors(agent_id: str):
    anchors = client.list_agent_anchors(agent_id)
    
    print(f'Found {len(anchors)} anchors:')
    for i, anchor in enumerate(anchors, 1):
        print(f'\n{i}. Anchor {anchor["id"]}')
        print(f'   Hash: {anchor["anchor_hash"]}')
        print(f'   Status: {anchor["status"]}')
        print(f'   Created: {anchor["created_at"]}')
        if anchor.get('anchor_tx_hash'):
            print(f'   TX: {anchor["anchor_tx_hash"]}')

# 5. Error handling
def anchor_with_error_handling(agent_id: str, data: dict):
    try:
        anchor = client.anchor_agent_data(
            agent_id=agent_id,
            data=data,
            description='Payment verification'
        )
        print(f'✅ Success: {anchor["id"]}')
        return anchor
        
    except client.NotFoundError:
        print(f'❌ Agent not found: {agent_id}')
    except client.ValidationError as e:
        print(f'❌ Invalid data format: {e}')
    except client.ServerError as e:
        print(f'❌ Server error: {e}')
    except Exception as e:
        print(f'❌ Unknown error: {e}')
        raise

# 6. Complete workflow
def main():
    agent_id = 'agent-550e8400-e29b-41d4-a716-446655440000'
    
    # Get current config
    get_config(agent_id)
    
    # Enable anchoring
    enable_anchoring(agent_id)
    
    # Anchor some data
    anchor_data(agent_id)
    
    # List all anchors
    list_anchors(agent_id)

if __name__ == '__main__':
    main()
```

---

## AI Agent Integration

### Overview

Deploy an autonomous XMTP agent that automatically anchors payment data on x402 micropayments.

### Quick Setup (5 minutes)

#### Step 1: Navigate to Agent Directory

```bash
cd agents/iso-x402-agent
```

#### Step 2: Install Dependencies

```bash
npm install
```

Expected output:
```
added 245 packages in 12s
```

#### Step 3: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

**Required configuration:**

```bash
# Anchoring Configuration
ANCHOR_ENABLED=true              # Enable anchoring feature
ANCHOR_ON_PAYMENT=true           # Auto-anchor on x402 payments
ANCHOR_WALLET=0x1234...          # Wallet for gas fees (optional)

# XMTP Configuration
XMTP_ENV=production              # or 'dev' for testing
WALLET_PRIVATE_KEY=0x...         # Agent's wallet private key

# ISO Middleware API
ISO_MW_API_URL=http://localhost:8000
ISO_MW_API_KEY=your_api_key      # Optional

# x402 Payment Configuration
X402_RECIPIENT=0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8
CHAIN_RPC_URL=https://mainnet.base.org
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Agent Settings
AGENT_NAME=ISO Anchoring Agent
LOG_LEVEL=info                   # debug, info, warn, error
```

#### Step 4: Build and Deploy

```bash
# Build TypeScript
npm run build

# Start agent
npm start
```

**Expected output:**

```
🤖 ISO Middleware XMTP Agent Starting...
✅ Environment: production
✅ XMTP client initialized
✅ Connected to ISO Middleware at http://localhost:8000
✅ Agent anchoring: ENABLED
✅ Auto-anchor on payment: ENABLED
✅ Anchor wallet: 0x1234...5678
✅ Listening for messages on XMTP...
```

### Available Commands

#### Status Check

```
User: status

Agent: 🔗 Agent Status

       Anchoring: ✅ Enabled
       Auto-anchor: ✅ Enabled
       Anchor wallet: 0x1234...5678
       Total anchors: 42
       Last anchor: 2 hours ago
       Last TX: 0xabcd...
```

#### Manual Anchor

```
User: anchor {"payment_id": "pay-123", "amount": 100.50}

Agent: ⏳ Creating anchor...
       
       ✅ Data anchored successfully!
       
       Anchor ID: 550e8400-e29b-41d4-a716-446655440000
       Hash: 0x1234567890abcdef...
       Status: pending
       
       View on Etherscan: https://etherscan.io/tx/0x...
```

#### List Recent Anchors

```
User: list anchors

Agent: 📋 Recent Anchors (5)

       1. 2 hours ago
          Hash: 0x1234...
          Status: ✅ Confirmed
          TX: 0xabcd...

       2. 4 hours ago
          Hash: 0x2345...
          Status: ✅ Confirmed
          TX: 0xbcde...

       3. 6 hours ago
          Hash: 0x3456...
          Status: ⏳ Pending
```

#### Verify Anchor

```
User: verify 0x1234567890abcdef...

Agent: 🔍 Verifying anchor...
       
       ✅ Anchor verified!
       
       Status: Confirmed
       Block: 12345678
       Timestamp: 2026-01-20 20:00:00 UTC
       Chain: ethereum
       Contract: 0x5678...
```

### Auto-Anchoring on Payments

When `ANCHOR_ON_PAYMENT=true`, the agent automatically anchors data on every x402 payment:

```
User: verify https://ipfs.io/ipfs/Qm...

Agent: ⏳ Verifying bundle (paying 0.001 USDC)...
       
       💳 Payment processed: 0.001 USDC
       🔗 Auto-anchoring payment data...
       
       ✅ Bundle verified!
       ✅ Data anchored!
       
       Verification:
         Valid: ✓ Yes
         Bundle hash: 0x1234...
       
       Anchor:
         Anchor hash: 0x5678...
         TX: 0xabcd...
         Status: pending
       
       💰 Payment: 0.001 USDC paid
```

### Deployment Options

#### Option 1: PM2 (Production)

```bash
# Install PM2
npm install -g pm2

# Start agent with PM2
pm2 start dist/index.js --name iso-anchor-agent

# Monitor
pm2 status
pm2 logs iso-anchor-agent

# Auto-restart on system reboot
pm2 startup
pm2 save
```

#### Option 2: Docker

```bash
# Build image
docker build -t iso-anchor-agent .

# Run container
docker run -d \
  --name iso-anchor-agent \
  --env-file .env \
  --restart unless-stopped \
  iso-anchor-agent

# View logs
docker logs -f iso-anchor-agent
```

#### Option 3: Cloud Platforms

**Heroku:**
```bash
heroku create iso-anchor-agent
heroku config:set ANCHOR_ENABLED=true
heroku config:set WALLET_PRIVATE_KEY=0x...
git push heroku main
```

**Railway:**
```bash
# Use railway.json configuration
railway up
```

**Google Cloud Run:**
```bash
gcloud run deploy iso-anchor-agent \
  --source . \
  --region us-central1 \
  --set-env-vars ANCHOR_ENABLED=true
```

### Monitoring

#### Health Checks

The agent exposes health metrics:

```bash
# Check agent health
curl http://localhost:3001/health

# Response:
{
  "status": "healthy",
  "uptime": 86400,
  "anchoring": {
    "enabled": true,
    "auto_on_payment": true,
    "total_anchors": 42,
    "last_anchor": "2026-01-20T20:00:00Z"
  }
}
```

#### Logs

Enable detailed logging:

```bash
LOG_LEVEL=debug npm start
```

Debug output example:
```
[2026-01-20T20:00:00.000Z] DEBUG: Received message from 0x1234...
[2026-01-20T20:00:00.100Z] DEBUG: Parsed command: { action: 'anchor', data: {...} }
[2026-01-20T20:00:00.200Z] DEBUG: Making payment of 0.001 USDC...
[2026-01-20T20:00:01.000Z] DEBUG: Payment successful: 0xabcd...
[2026-01-20T20:00:01.200Z] DEBUG: Creating anchor...
[2026-01-20T20:00:02.000Z] DEBUG: Anchor created: 0x1234...
[2026-01-20T20:00:02.100Z] DEBUG: Sent reply to 0x1234...
```

---

## API Reference

### Endpoints

#### Get Anchoring Configuration

```http
GET /v1/agents/{agent_id}/anchoring-config
```

**Response:**
```json
{
  "auto_anchor_enabled": false,
  "anchor_on_payment": false,
  "anchor_wallet": null
}
```

#### Update Anchoring Configuration

```http
PUT /v1/agents/{agent_id}/anchoring-config
```

**Request:**
```json
{
  "auto_anchor_enabled": true,
  "anchor_on_payment": true,
  "anchor_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

**Response:**
```json
{
  "auto_anchor_enabled": true,
  "anchor_on_payment": true,
  "anchor_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

#### Anchor Data

```http
POST /v1/agents/{agent_id}/anchor-data
```

**Request:**
```json
{
  "data": {
    "payment_id": "pay-001",
    "amount": 100.50,
    "currency": "USD"
  },
  "description": "Payment verification"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent-550e8400-e29b-41d4-a716-446655440000",
  "anchor_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "anchor_tx_hash": null,
  "anchor_contract": null,
  "status": "pending",
  "created_at": "2026-01-20T20:00:00Z"
}
```

#### List Anchors

```http
GET /v1/agents/{agent_id}/anchors
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_id": "agent-550e8400-e29b-41d4-a716-446655440000",
    "anchor_hash": "0x1234...",
    "anchor_tx_hash": "0xabcd...",
    "anchor_contract": "0x5678...",
    "status": "confirmed",
    "created_at": "2026-01-20T20:00:00Z"
  }
]
```

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 404 | Agent not found | Verify agent ID |
| 422 | Invalid data | Check JSON format |
| 500 | Server error | Check API logs |
| 503 | Blockchain unavailable | Check RPC endpoint |

---

## Troubleshooting

### Common Issues

#### 1. Anchor stuck in "pending" status

**Symptoms:** Anchor shows "pending" for > 10 minutes

**Causes:**
- Insufficient gas in anchor wallet
- Network congestion
- RPC endpoint issues

**Solutions:**
```bash
# Check wallet balance
cast balance 0xYourAnchorWallet --rpc-url https://mainnet.base.org

# Increase gas price in agent config
# Edit .env:
GAS_PRICE_GWEI=50  # Increase if network is congested

# Check RPC endpoint
curl https://mainnet.base.org \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

#### 2. SDK connection timeout

**Symptoms:** `Error: connect ETIMEDOUT` or `Error: Network request failed`

**Solutions:**
```typescript
// Increase timeout
const client = new IsoMiddlewareClient({
  baseUrl: 'http://localhost:8000',
  timeout: 30000  // 30 seconds
});

// Check API is running
// curl http://localhost:8000/health

// Check firewall/network
// ping localhost
```

#### 3. Invalid JSON error

**Symptoms:** `422 Unprocessable Entity: Invalid JSON`

**Solutions:**
```json
// ❌ Invalid (has trailing comma)
{
  "payment_id": "pay-001",
  "amount": 100.50,
}

// ✅ Valid
{
  "payment_id": "pay-001",
  "amount": 100.50
}

// Validate at: https://jsonlint.com/
```

#### 4. Agent not receiving XMTP messages

**Symptoms:** Agent running but no response to messages

**Solutions:**
```bash
# Check XMTP environment
# Ensure sender and agent are on same network (dev/production)

# Check wallet has XMTP identity
# Visit: https://converse.xyz to initialize if needed

# Verify agent logs
tail -f agent.log | grep XMTP

# Check XMTP_ENV matches sender's network
XMTP_ENV=production  # or 'dev'
```

---

## Architecture

### How It Works

```
┌─────────────┐
│   User/AI   │
│    Agent    │
└──────┬──────┘
       │ 1. Configure anchoring
       ▼
┌─────────────────────────────────┐
│  ISO Middleware API             │
│  - Stores configuration         │
│  - Manages anchor records       │
└──────┬──────────────────────────┘
       │ 2. On payment/manual trigger
       ▼
┌─────────────────────────────────┐
│  Anchoring Service              │
│  - Hash data (SHA-256)          │
│  - Create anchor record         │
│  - Submit to blockchain         │
└──────┬──────────────────────────┘
       │ 3. Blockchain transaction
       ▼
┌─────────────────────────────────┐
│  EVM Chain (Ethereum/Base/etc)  │
│  - EvidenceAnchor contract      │
│  - Stores hash on-chain         │
│  - Emits event                  │
└──────┬──────────────────────────┘
       │ 4. Confirmation
       ▼
┌─────────────────────────────────┐
│  Anchor Record Updated          │
│  - Status: confirmed            │
│  - TX hash stored               │
│  - Block number recorded        │
└─────────────────────────────────┘
```

### Data Flow

1. **Configuration**: User enables anchoring via UI/SDK/Agent
2. **Trigger**: Payment processed or manual anchor requested
3. **Hashing**: Data is hashed with SHA-256
4. **Recording**: Anchor record created in database
5. **Submission**: Hash submitted to blockchain contract
6. **Confirmation**: Transaction mined and verified
7. **Update**: Anchor record updated with TX details

### Smart Contracts

```solidity
// EvidenceAnchorBasic.sol (simplified)
contract EvidenceAnchorBasic {
    event EvidenceAnchored(
        bytes32 indexed dataHash,
        address indexed submitter,
        uint256 timestamp
    );
    
    function anchorEvidence(bytes32 dataHash) external {
        emit EvidenceAnchored(dataHash, msg.sender, block.timestamp);
    }
}
```

---

## Advanced Topics

### Multi-Chain Anchoring

Anchor the same data to multiple chains:

```typescript
// Configure multi-chain anchoring
await client.updateAgentAnchoringConfig(agentId, {
  auto_anchor_enabled: true,
  chains: ['ethereum', 'base', 'optimism']
});

// Each chain gets its own anchor record
const anchors = await client.listAgentAnchors(agentId);
// Returns anchors for all configured chains
```

### Custom Anchor Contracts

Deploy your own anchor contract:

```bash
# Deploy contract
cd contracts
npx hardhat run scripts/deploy.js --network base

# Configure agent to use custom contract
await client.updateAgentAnchoringConfig(agentId, {
  anchor_contract: '0xYourContractAddress'
});
```

### Batch Anchoring

Anchor multiple data points efficiently:

```typescript
// Batch anchor (coming soon)
const anchors = await client.batchAnchorAgentData(agentId, [
  { data: { payment_id: 'pay-001' }, description: 'Payment 1' },
  { data: { payment_id: 'pay-002' }, description: 'Payment 2' },
  { data: { payment_id: 'pay-003' }, description: 'Payment 3' }
]);

// More efficient: single transaction, multiple hashes
```

### Gas Optimization

Tips for reducing gas costs:

1. **Use Layer 2**: Deploy on Base/Optimism instead of Ethereum mainnet
2. **Batch anchors**: Combine multiple anchors into single transaction
3. **Monitor gas prices**: Anchor during low-traffic periods
4. **Use dedicated wallet**: Separate anchor wallet with appropriate gas budget

---

## Security

### Best Practices

1. **Wallet Security**
   - Use dedicated wallet for anchoring (not main funds)
   - Store private keys in secure environment variables
   - Rotate keys periodically
   - Never commit keys to version control

2. **Data Privacy**
   - Only hashes are stored on-chain (not raw data)
   - Original data stored in encrypted database
   - Consider data sensitivity before anchoring

3. **Access Control**
   - Anchoring configuration requires agent ownership
   - API endpoints use standard authentication
   - Anchor verification is publicly accessible

4. **Gas Management**
   - Monitor anchor wallet balance
   - Set gas limits to prevent excessive spending
   - Alert on low balance

### Audit Trail

Every anchor creates an immutable audit trail:

```
Data → Hash (SHA-256) → Blockchain → Permanent Record
```

Anyone can verify:
1. Data was anchored at specific time
2. Data hasn't been tampered with
3. Anchor transaction is confirmed on-chain

---

## FAQ

**Q: How much does anchoring cost?**
A: Gas fees vary by network. Base: ~$0.01, Ethereum: ~$1-5, Optimism: ~$0.05

**Q: Can I anchor private data?**
A: Yes, only the hash goes on-chain. Original data stays private in your database.

**Q: How long until anchor is confirmed?**
A: 15 seconds on Base, 12 seconds on Ethereum, 2 seconds on Optimism (average).

**Q: What if anchoring fails?**
A: Anchor record shows "failed" status. Check logs for details. Common causes: insufficient gas, invalid data.

**Q: Can I delete an anchor?**
A: No, blockchain records are immutable. You can mark as inactive in your database.

**Q: Do I need my own blockchain node?**
A: No, uses public RPC endpoints by default. You can configure custom RPC if desired.

---

## Resources

### Documentation
- [Full API Documentation](../API_Documentation.md)
- [Technical Documentation](../docs/AGENT_ANCHORING.md)
- [x402 Protocol Guide](../docs/X402_INTEGRATION.md)
- [XMTP Agents Guide](../docs/AGENTS_GUIDE.md)

### Examples
- [TypeScript SDK Examples](../packages/sdk/README.md)
- [Python SDK Examples](../packages/sdk-python/README.md)
- [Agent Templates](../agents/)

### Tools
- [Etherscan](https://etherscan.io) - Ethereum block explorer
- [BaseScan](https://basescan.org) - Base block explorer
- [JSONLint](https://jsonlint.com) - JSON validator
- [web3.storage](https://web3.storage) - IPFS storage


**Built with ❤️ for ISO 20022 compliance and blockchain immutability**
