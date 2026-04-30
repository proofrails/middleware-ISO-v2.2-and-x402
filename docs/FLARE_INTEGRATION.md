# Flare Blockchain Integration

This document covers everything specific to the Flare network: FTSO v2 on-chain price feeds, native FLR payments via the x402 protocol, and the proactive monitoring loop.

---

## Table of Contents

1. [FTSO v2 — On-Chain Price Feeds](#1-ftso-v2--on-chain-price-feeds)
2. [FLR Native Payments via x402](#2-flr-native-payments-via-x402)
3. [Proactive Monitoring Loop](#3-proactive-monitoring-loop)
4. [Environment Variable Reference](#4-environment-variable-reference)
5. [Architecture Diagram](#5-architecture-diagram)

---

## 1. FTSO v2 — On-Chain Price Feeds

### What is FTSO v2?

The Flare Time Series Oracle (FTSO) is a decentralised, on-chain price oracle built into the Flare network. Independent data providers submit prices every ~90 seconds; the protocol aggregates them and commits a finalised value directly to Flare's C-Chain (EVM). No trusted third party is involved.

**Why it matters for ISO 20022 compliance**: Every `pain.001` message that carries an exchange rate can now reference a cryptographically verifiable, on-chain source rather than a centralised API quote. Auditors can trace the exact rate back to the on-chain epoch and verify it themselves.

### How this middleware uses FTSO

**Automatic injection**: Whenever a receipt is submitted with `chain=flare` (or `flare-testnet`, `coston2`, `coston`), the background job automatically fetches the current FLR/USD rate (or the feed matching the payment currency) from FTSO v2 and embeds it in the ISO message:

```
POST /v1/iso/record-tip
{
  "tip_tx_hash": "0x...",
  "chain":       "flare",
  "amount":      "150.00",
  "currency":    "FLR",
  ...
}

→ pain001.xml contains:
   <Amt>
     <InstdAmt Ccy="FLR">150</InstdAmt>
     <EqvtAmt Ccy="USD">3.22</EqvtAmt>
     <XchgRateInf>
       <XchgRate>0.02150</XchgRate>
       <RateSrc>ftso_v2</RateSrc>
       <Desc>FLR/USD</Desc>
       <Dt>2026-04-27T10:23:40+00:00</Dt>
     </XchgRateInf>
   </Amt>
```

The `fx.json` artifact in each evidence bundle carries the full raw data:

```json
{
  "base_ccy":      "USD",
  "quote_ccy":     "FLR",
  "provider":      "ftso_v2",
  "feed":          "FLR/USD",
  "rate":          "0.02150",
  "raw_value":     21500000,
  "raw_decimals":  -9,
  "source":        "ftso_v2",
  "on_chain":      true,
  "ts":            "2026-04-27T10:23:40"
}
```

`raw_value * 10^raw_decimals = actual_price`.  Anyone with Flare RPC access can verify this independently.

### Supported feeds

| Symbol     | Description                |
|------------|----------------------------|
| `FLR/USD`  | Flare native token         |
| `SGB/USD`  | Songbird (Flare canary)    |
| `BTC/USD`  | Bitcoin                    |
| `ETH/USD`  | Ethereum                   |
| `XRP/USD`  | XRP (XRPL bridge asset)    |
| `USDC/USD` | USDC (reference)           |
| `USDT/USD` | Tether (reference)         |
| `ADA/USD`  | Cardano                    |
| `DOGE/USD` | Dogecoin                   |
| `ALGO/USD` | Algorand                   |

To add a feed, append its symbol to `FEED_IDS` in `app/flare/ftso.py`. The encoding is `0x01` + ASCII symbol + zero-padding to 21 bytes.

### On-demand FTSO rate lookup (x402-gated)

```http
POST /v1/x402/premium/fx-lookup
X-PAYMENT: {"tx_hash":"0x...","amount":"0.001","recipient":"0x...","currency":"USDC","chain":"base"}
Content-Type: application/json

{
  "base_ccy":  "USD",
  "quote_ccy": "FLR",
  "provider":  "ftso"
}
```

Response:
```json
{"rate": "0.02150", "source": "ftso_v2"}
```

Or pay with FLR directly (see [Section 2](#2-flr-native-payments-via-x402)).

### Monitor FTSO snapshot (free, no auth)

The monitoring loop refreshes all feeds every cycle. Get the cached snapshot:

```http
GET /v1/monitor/ftso
GET /v1/monitor/ftso?feed=FLR/USD
```

Response:
```json
{
  "FLR/USD": {
    "value":       "0.02150",
    "timestamp":   1745753020,
    "age_seconds": 43.2,
    "source":      "ftso_v2"
  }
}
```

### Python API

```python
from app.flare.ftso import get_ftso_rate, get_ftso_rates, FTSORate

# Single feed
rate: FTSORate | None = get_ftso_rate("FLR/USD")
if rate:
    print(rate.value)         # Decimal("0.02150")
    print(rate.timestamp)     # 1745753020  (unix epoch)
    print(rate.age_seconds)   # 43.2

# Batched (single RPC call)
rates = get_ftso_rates(["FLR/USD", "BTC/USD", "ETH/USD"])
```

### Contract addresses

| Contract              | Flare mainnet address                        |
|-----------------------|----------------------------------------------|
| `FlareContractRegistry` | `0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019` |
| `FtsoV2`              | Resolved dynamically via registry            |
| `EvidenceAnchor`      | `0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8` |

---

## 2. FLR Native Payments via x402

### Overview

All premium endpoints previously accepted only USDC on Base. They now accept **two payment options** in parallel:

| Option | Token | Chain | Verification method |
|--------|-------|-------|---------------------|
| 1 (primary) | USDC | Base mainnet | ERC-20 Transfer event log |
| 2 (Flare-native) | FLR | Flare C-Chain | Native ETH-value transfer check |

The server returns both options in the HTTP 402 body so any agent can choose the cheapest or most convenient path.

### HTTP 402 response format

When no `X-PAYMENT` header is provided:

```http
HTTP/1.1 402 Payment Required
X-Payment-Required: true
X-Payment-Amount: 0.001
X-Payment-Currency: USDC

{
  "amount":    "0.001",
  "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  "reference": "x402:premium_verify_bundle:1745753020.123",
  "currency":  "USDC",
  "chain":     "base",
  "accepted": [
    {
      "amount":    "0.001",
      "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
      "currency":  "USDC",
      "chain":     "base",
      "reference": "..."
    },
    {
      "amount":    "0.05",
      "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
      "currency":  "FLR",
      "chain":     "flare",
      "reference": "..."
    }
  ]
}
```

### Paying with FLR — step by step

1. **Read the 402 body** — find the `accepted` option with `"currency": "FLR"`.
2. **Send a native FLR transfer** to the listed `recipient` for the listed `amount`.
   - Use any Flare wallet (ethers.js, web3.py, MetaMask, etc.).
   - FLR is the native token of Flare C-Chain (chain ID 14), so no ERC-20 approval is needed.
3. **Retry with the `X-PAYMENT` header**:

```http
POST /v1/x402/premium/verify-bundle
X-PAYMENT: {
  "tx_hash":   "0x<your-flr-transfer-txhash>",
  "amount":    "0.05",
  "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
  "currency":  "FLR",
  "chain":     "flare"
}
```

4. The server calls `X402PaymentVerifier._verify_flr_payment()` which:
   - Gets the transaction receipt from Flare C-Chain (checks status == 1).
   - Confirms `tx.to == recipient` (case-insensitive).
   - Confirms `tx.value >= expected_amount_in_wei` (allows ±0.001 FLR tolerance).

### FLR price table (defaults, adjustable via env)

| Endpoint | USDC price | FLR equivalent | Env var |
|----------|-----------|----------------|---------|
| `verify-bundle` | 0.001 | 0.05 | `X402_FLR_VERIFY` |
| `generate-statement` | 0.005 | 0.25 | `X402_FLR_STATEMENT` |
| `iso-message` | 0.002 | 0.10 | `X402_FLR_ISO_MSG` |
| `fx-lookup` | 0.001 | 0.05 | `X402_FLR_FX_LOOKUP` |
| `bulk-verify` | 0.010 | 0.50 | `X402_FLR_BULK` |
| `refund` | 0.003 | 0.15 | `X402_FLR_REFUND` |

FLR amounts should be updated when the FLR/USD rate changes significantly. A future enhancement will auto-scale them from the FTSO oracle.

### Example: agent paying with FLR (Python)

```python
from web3 import Web3
from decimal import Decimal
import json

w3 = Web3(Web3.HTTPProvider("https://flare-api.flare.network/ext/C/rpc"))
acct = w3.eth.account.from_key("0x<your-private-key>")

RECIPIENT = "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8"
amount_flr = Decimal("0.05")
amount_wei = int(amount_flr * Decimal(10 ** 18))

# 1. Send FLR
tx = {
    "to": RECIPIENT,
    "value": amount_wei,
    "gas": 21000,
    "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
    "nonce": w3.eth.get_transaction_count(acct.address),
    "chainId": 14,  # Flare mainnet
}
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()
w3.eth.wait_for_transaction_receipt(tx_hash)

# 2. Call premium endpoint
import requests
payment_header = json.dumps({
    "tx_hash": tx_hash,
    "amount": str(amount_flr),
    "recipient": RECIPIENT,
    "currency": "FLR",
    "chain": "flare",
})
resp = requests.post(
    "https://your-middleware/v1/x402/premium/verify-bundle",
    headers={"X-PAYMENT": payment_header},
    json={"bundle_url": "https://..."},
)
print(resp.json())
```

---

## 3. Proactive Monitoring Loop

### Overview

The monitoring service (`app/monitor.py`) runs as a daemon thread inside the FastAPI process. It performs four tasks every `MONITOR_INTERVAL_SECONDS` (default: 60 s):

```
                    ┌─────────────────────────────────┐
                    │        MonitorService            │
                    │        (daemon thread)           │
                    │                                  │
Every N seconds:    │  1. _recover_stale_anchors()     │
                    │  2. _refresh_ftso_rates()        │
                    │  3. _watch_wallets()  [optional] │
                    │  4. _maybe_generate_batch_reports│
                    │     ()                [optional] │
                    └─────────────────────────────────┘
```

### Task 1: Stale anchor recovery

Receipts sometimes get stuck in `awaiting_anchor` if the anchor worker crashes or the RPC times out. The monitor detects receipts with:
- `status = 'awaiting_anchor'`
- `flare_txid IS NULL`
- `created_at < NOW() - MONITOR_STALE_ANCHOR_MINUTES`

...and re-enqueues them to the anchor queue. Maximum 20 per cycle to avoid thundering herd.

**No configuration needed** — this runs whenever the monitor is enabled.

### Task 2: FTSO price refresh

Every cycle the monitor fetches all supported FTSO feeds and stores them in memory. This powers the `GET /v1/monitor/ftso` endpoint without an RPC call per HTTP request.

### Task 3: Wallet watcher

When `MONITOR_WALLET_WATCH_ENABLED=true`, the monitor polls Flare C-Chain for new incoming native FLR transfers to registered wallets and **automatically creates ISO receipts**.

**Register a wallet:**

```http
POST /v1/monitor/wallets
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "address": "0xYourWalletAddress",
  "label":   "Treasury wallet"
}
```

The monitor will scan up to 200 blocks per cycle for each registered wallet. When a new transfer is found it:
1. Creates a `Receipt` row with `status=pending`.
2. Enqueues it to the default RQ queue.
3. The worker generates the ISO bundle and anchors it on Flare — exactly as if the transfer was submitted via `POST /v1/iso/record-tip`.

**List watched wallets:**

```http
GET /v1/monitor/wallets
Authorization: Bearer <api-key>
```

**Unwatch:**

```http
DELETE /v1/monitor/wallets/0xYourWalletAddress
Authorization: Bearer <api-key>
```

### Task 4: Daily batch reports

When `MONITOR_BATCH_REPORTS_ENABLED=true`, on the first monitor cycle of each UTC day the service generates a `camt.053` (Bank-to-Customer Statement) for all anchored receipts from the previous day and writes it to `artifacts/statements/camt053_<date>.xml`.

This can be served via `GET /files/statements/camt053_2026-04-26.xml` (the artifacts directory is mounted as `/files`).

### Monitor status API

```http
GET /v1/monitor/status
Authorization: Bearer <api-key>
```

Response:
```json
{
  "running":                  true,
  "started_at":               "2026-04-27T08:00:00",
  "last_run_at":              "2026-04-27T10:23:00",
  "cycles_completed":         142,
  "stale_anchors_recovered":  3,
  "wallets_watched":          2,
  "new_receipts_auto_created": 17,
  "batch_reports_generated":  1,
  "last_ftso_rates": {
    "FLR/USD": {"value": "0.02150", "timestamp": 1745753020, "age_seconds": 43}
  },
  "recent_errors": []
}
```

---

## 4. Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `FLARE_RPC_URL` | `https://flare-api.flare.network/ext/C/rpc` | Flare C-Chain RPC for anchoring |
| `FTSO_ENABLED` | `true` | Enable FTSO rate injection in ISO messages |
| `FTSO_CACHE_TTL` | `90` | Seconds to cache FTSO feed values |
| `FTSO_REGISTRY_ADDRESS` | `0xaD67FE66...` | FlareContractRegistry (change only on major upgrades) |
| `X402_FLARE_RPC_URL` | (same as FLARE_RPC_URL) | RPC used for FLR payment verification |
| `X402_RECIPIENT_ADDRESS` | `0x0690d8cF...` | USDC recipient on Base |
| `X402_FLR_RECIPIENT` | (same as above) | FLR recipient on Flare |
| `X402_FLR_VERIFY` | `0.05` | FLR price for verify-bundle |
| `X402_FLR_STATEMENT` | `0.25` | FLR price for generate-statement |
| `X402_FLR_ISO_MSG` | `0.10` | FLR price for iso-message lookup |
| `X402_FLR_FX_LOOKUP` | `0.05` | FLR price for fx-lookup |
| `X402_FLR_BULK` | `0.50` | FLR price for bulk-verify |
| `X402_FLR_REFUND` | `0.15` | FLR price for refund |
| `MONITOR_ENABLED` | `true` | Master switch for monitoring loop |
| `MONITOR_INTERVAL_SECONDS` | `60` | Seconds between monitor cycles |
| `MONITOR_STALE_ANCHOR_MINUTES` | `10` | Minutes before a stuck anchor is retried |
| `MONITOR_WALLET_WATCH_ENABLED` | `false` | Enable automatic wallet watching |
| `MONITOR_BATCH_REPORTS_ENABLED` | `false` | Enable daily camt.053 generation |

---

## 5. Architecture Diagram

```
                        Flare C-Chain (chain ID 14)
                        ┌────────────────────────────────────┐
                        │                                    │
                        │  FlareContractRegistry             │
                        │  └─► FtsoV2                        │
                        │       └─► getFeedById(bytes21)     │
                        │           ├─► FLR/USD rate         │
                        │           └─► BTC/USD rate ...     │
                        │                                    │
                        │  EvidenceAnchor contract           │
                        │  └─► anchorEvidence(bytes32)       │
                        │                                    │
                        └────────────────────────────────────┘
                               ▲                ▲
                    FTSO read  │    anchor tx   │  FLR payment tx
                               │                │
                   ┌───────────────────────────────────────────────┐
                   │           ISO Middleware (FastAPI)             │
                   │                                               │
                   │  ┌──────────────┐  ┌────────────────────────┐│
                   │  │ FTSO module  │  │  x402 verifier         ││
                   │  │ app/flare/   │  │  ├─ USDC (Base)        ││
                   │  │ ftso.py      │  │  └─ FLR  (Flare)       ││
                   │  └──────┬───────┘  └────────────────────────┘│
                   │         │                                     │
                   │  ┌──────▼──────────────────────────────────┐ │
                   │  │  Background jobs (RQ workers)           │ │
                   │  │  process_receipt_job()                  │ │
                   │  │  └─► auto-inject FTSO rate              │ │
                   │  │  └─► generate ISO XML with rate source  │ │
                   │  │  anchor_receipt_job()                   │ │
                   │  │  └─► submit bundle hash to Flare        │ │
                   │  └─────────────────────────────────────────┘ │
                   │                                               │
                   │  ┌──────────────────────────────────────────┐│
                   │  │  Monitor daemon thread                   ││
                   │  │  ├─ stale anchor recovery               ││
                   │  │  ├─ FTSO price cache refresh            ││
                   │  │  ├─ wallet watcher (optional)           ││
                   │  │  └─ daily camt.053 reports (optional)   ││
                   │  └──────────────────────────────────────────┘│
                   └───────────────────────────────────────────────┘
                               │
                        ┌──────▼──────┐
                        │  AI Agent   │
                        │  (XMTP)     │
                        │  pays FLR   │
                        │  or USDC    │
                        └─────────────┘
```
