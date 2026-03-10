# ISO Middleware — Mock Producer

A standalone service that generates synthetic “tips” and posts them to the ISO Middleware API (POST /v1/iso/record-tip). It does not modify the existing middleware, UIs, or backend. It’s intended for demos, load/scenario testing, and local development.

Key properties
- Non-invasive: separate service, no code changes to middleware or UIs
- Real API usage: calls the actual middleware endpoints so receipts are created and processed normally
- Flexible scenarios: rate-based generator, single-send, replay inputs, optional callback handling, metrics
- Documented behavior: dedupe-safe payloads, idempotency notes, and clear configuration

## Contents

- Overview
- Requirements
- Quickstart
- Configuration (.env)
- REST API
- Scenarios & Replay
- Callback flow
- Metrics & Observability
- Dedupe & Idempotency
- Security & Limits
- Troubleshooting
- Non-goals

---

## Overview

This service simulates a producer (e.g., Capella or any app) by sending POST /v1/iso/record-tip payloads. The middleware will:
- Immediately create a receipt (status=pending)
- Run background processing (generate pain.001, evidence.zip, optional VC)
- Attempt anchoring (if chain env set in middleware), then update status to anchored
- Emit SSE updates and optionally POST a callback when configured

Use this to populate receipts in:
- Newest UI: http://localhost:3000 (web-alt)
- Static live page: http://127.0.0.1:8000/receipt/{receipt_id}
- API: GET /v1/receipts, GET /v1/iso/receipts/{id}

## Requirements

- Node.js >= 18.17
- Middleware backend running at http://127.0.0.1:8000 (or your configured URL)
- If middleware auth is enabled, an API key (X-API-Key)

## Quickstart

1) Install
```
npm --prefix mock-producer install
```

2) Configure (optional)
- Copy mock-producer/.env.example to mock-producer/.env and adjust:
```
MW_BASE_URL=http://127.0.0.1:8000
API_KEY=           # leave empty if middleware dev auth is disabled
DEFAULT_CHAIN=flare
DEFAULT_CURRENCY=FLR
CALLBACK_BASE_URL= # e.g. http://localhost:4001 to enable callbacks
PORT=4001
```

3) Run
```
cd mock-producer
npm run dev
```
- Health: http://localhost:4001/health
- Metrics: http://localhost:4001/metrics

4) Start a scenario (30 tips/min for 5 min)
```
curl -X POST http://localhost:4001/scenarios/start ^
  -H "Content-Type: application/json" ^
  -d "{\"rate\":30,\"durationSec\":300,\"chain\":\"flare\",\"currency\":\"FLR\",\"callback\":true}"
```

5) Check status
```
curl http://localhost:4001/status
```

6) Stop scenario
```
curl -X POST http://localhost:4001/scenarios/stop
```

7) Send a single tip
```
curl -X POST http://localhost:4001/one -H "Content-Type: application/json" -d "{}"
```

## Configuration (.env)

- MW_BASE_URL: Middleware API base (default http://127.0.0.1:8000)
- API_KEY: Optional X-API-Key (if middleware auth enabled)
- DEFAULT_CHAIN: Default chain for generated tips (default flare)
- DEFAULT_CURRENCY: Default currency (default FLR)
- CALLBACK_BASE_URL: If set (e.g., http://localhost:4001), the producer includes a callback_url in record-tip; middleware will POST results back to /callback
- PORT: Service port (default 4001)

You can update a subset of config at runtime:
```
curl -X POST http://localhost:4001/config ^
  -H "Content-Type: application/json" ^
  -d "{\"MW_BASE_URL\":\"http://127.0.0.1:8000\",\"API_KEY\":\"dev123\"}"
```

## REST API

- GET /health → {status, ts, version}
- GET /metrics → Prometheus metrics (prom-client)
- POST /scenarios/start
  - Body: { rate:number, durationSec?:number, chain?:string, currency?:string, amountMin?:string, amountMax?:string, seed?:string, failurePct?:number, referencePrefix?:string, callback?:boolean }
  - Starts sending tips at rate tips/min. Auto-stops after durationSec if provided.
- POST /scenarios/stop → Stops the running scenario
- GET /status → { running, startedAt, sent, errors, params }
- POST /one
  - Body: Optional overrides { chain, currency, amount, reference, sender_wallet, receiver_wallet, callback:boolean, referencePrefix }
  - Sends a single tip
- POST /replay
  - Body: { items: Array<{ tip_tx_hash, chain, amount, currency, sender_wallet, receiver_wallet, reference, callback_url? }> }
  - Replays specific payloads exactly
- POST /reset → Resets counters
- POST /config → Runtime update allowed keys (MW_BASE_URL, API_KEY, DEFAULT_CHAIN, DEFAULT_CURRENCY, CALLBACK_BASE_URL)
- POST /callback → Receives middleware callbacks (if callback enabled); logs best-effort

## Scenarios & Replay

- Scenarios:
  - rate: tips per minute (min interval 200ms safety)
  - durationSec: optional stop after N seconds
  - Randomized amount range via amountMin/amountMax
  - Unique tip_tx_hash and reference for dedupe safety
  - Optional callback when CALLBACK_BASE_URL is set
- Replay:
  - Provide an array of exact items to send; useful for deterministic tests or reproductions

## Callback flow

- If CALLBACK_BASE_URL is set, the service passes callback_url to /v1/iso/record-tip.
- Middleware will POST a summary (receipt id, status, artifacts, txid, etc.) to the producer’s /callback.
- The producer logs these (stdout). Extend to persist as needed.

## Metrics & Observability

- mock_producer_tips_sent_total
- mock_producer_errors_total
- mock_producer_running (gauge)
- mock_producer_rate_per_min (gauge)
- Default process metrics via prom-client
- Logs: structured JSON can be added; currently console logs for callback and startup

## Dedupe & Idempotency

Middleware dedupes by:
- (chain, tip_tx_hash)
- reference

The generator ensures unique values unless you explicitly replay items. If you re-use the same values, the middleware may return an existing receipt.

## Security & Limits

- Do not commit real API keys; use .env or runtime vars
- Set reasonable rates in dev; consider uvicorn workers and DB limits before stress testing
- This service only generates inputs; anchoring and verification happen in the middleware

## Troubleshooting

- 401 Unauthorized → Set API_KEY to match middleware
- Anchoring failed → Ensure middleware has FLARE_RPC_URL, ANCHOR_CONTRACT_ADDR, ANCHOR_PRIVATE_KEY (funded)
- Empty UI list → Make sure scenario is running; check /status; verify dedupe uniqueness
- CORS/UI → UI concerns don’t apply to mock-producer; it only calls middleware

## Non-goals

- Not a chain simulator; no on-chain writes here
- Not a replacement for the middleware’s verification or anchoring logic
- Not persisting callback payloads (demo/log only by default)
