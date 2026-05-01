# x402 Payments

x402 is an HTTP payment protocol that lets clients pay for API access using on-chain transfers. The name refers to HTTP 402 Payment Required, a status code defined in 1996 and left unused until micropayments became practical.

## Supported chains

| Currency | Chain | Notes |
|----------|-------|-------|
| USDC | Base mainnet | ERC-20 transfer, 6 decimals |
| FLR | Flare C-Chain | Native token transfer |

The server accepts either. The 402 response body lists both options and the client chooses.

## Protocol flow

```
Client                          ProofRails (server)
  |                                     |
  |-- POST /v1/x402/premium/verify ---> |
  |                                     |-- (no X-PAYMENT header)
  |<-- 402 Payment Required ------------|
  |    { "accepted": [                  |
  |        { "amount": "0.001",         |
  |          "currency": "USDC",        |
  |          "chain": "base",           |
  |          "recipient": "0x..." },    |
  |        { "amount": "0.05",          |
  |          "currency": "FLR",         |
  |          "chain": "flare",          |
  |          "recipient": "0x..." }     |
  |      ] }                            |
  |                                     |
  |-- (client sends USDC on Base        |
  |    OR FLR on Flare) ------------>   Blockchain
  |<-- tx confirmed -------------------|
  |                                     |
  |-- POST /v1/x402/premium/verify ---> |
  |    X-PAYMENT: { tx_hash, amount,    |
  |                 recipient,          |
  |                 currency, chain }   |
  |                                     |-- verify tx on correct chain
  |                                     |-- record payment
  |<-- 200 { result... } ---------------|
```

## Payment verification

In production mode, the middleware:

1. Parses the `X-PAYMENT` header as JSON.
2. Selects the verifier for the declared chain (`base` → USDC ERC-20 log check; `flare` → native FLR value check).
3. Confirms: correct recipient, correct amount, transaction confirmed.
4. Rejects reused tx hashes.
5. Records the payment in `x402_payments`.

In development mode (`X402_MOCK_PAYMENTS=true`), on-chain verification is skipped. This is for local development and tests only — never set in production.

## Premium endpoints

| Endpoint | USDC price | FLR price | Function |
|----------|-----------|-----------|---------|
| `POST /v1/x402/premium/verify-bundle` | 0.001 | 0.05 | Verify an evidence bundle |
| `POST /v1/x402/premium/generate-statement` | 0.005 | 0.25 | Generate a camt.053 statement |
| `POST /v1/x402/premium/fx-lookup` | 0.0005 | 0.05 | Current FX rate (FTSO) |
| `POST /v1/x402/premium/bulk-verify` | 0.01 | 0.50 | Verify multiple bundles |
| `POST /v1/x402/premium/refund` | 0.001 | 0.15 | Initiate a refund |

FLR prices are configurable via env vars (`X402_FLR_VERIFY`, `X402_FLR_STATEMENT`, etc.). Current pricing: `GET /v1/x402/pricing`.

## Environment variables

```env
X402_RECIPIENT=0x...          # USDC recipient address on Base
X402_FLR_RECIPIENT=0x...      # FLR recipient on Flare (defaults to X402_RECIPIENT)
X402_MOCK_PAYMENTS=true       # DEV ONLY — skip on-chain verification
X402_FLR_VERIFY=0.05          # FLR price for verify-bundle
X402_FLR_STATEMENT=0.25       # FLR price for generate-statement
X402_FLR_ISO_MSG=0.10         # FLR price for iso-message
X402_FLR_FX_LOOKUP=0.05       # FLR price for fx-lookup
X402_FLR_BULK=0.50            # FLR price for bulk-verify
X402_FLR_REFUND=0.15          # FLR price for refund
```

## Analytics

- `GET /v1/x402/payments` — list verified payments (auth required)
- `GET /v1/x402/revenue?days=7` — revenue summary (admin only)

## Agent auto-anchoring

When an agent has `anchor_on_payment=true`, each verified x402 payment automatically triggers a background anchor task that writes the payment hash to the Flare anchor contract.

## See also

- [Use x402 Paid Endpoints](../guides/use-x402-paid-endpoints.md)
- [API: x402](../api/x402.md)
- [Agentic Workflows](./agentic-workflows.md)
