# x402 Payments

x402 is an HTTP payment protocol that lets clients pay for API access using on-chain stablecoin transfers. The name refers to HTTP 402 Payment Required, a status code defined in 1996 and left unused until micropayments became practical.

## Protocol flow

```
Client                          ProofRails (server)
  |                                     |
  |-- POST /v1/x402/premium/verify ---> |
  |                                     |-- (no X-PAYMENT header)
  |<-- 402 Payment Required ------------|
  |    { "accepted": [{ "amount": "0.001", "currency": "USDC",
  |                     "recipient": "0x...", "chain": "base" }],
  |      "x-payment-required": "true" }  |
  |                                     |
  |-- (client sends USDC on Base) ----> Blockchain
  |<-- tx confirmed -------------------|
  |                                     |
  |-- POST /v1/x402/premium/verify ---> |
  |    X-PAYMENT: { tx_hash, amount,    |
  |                 recipient, currency, chain }
  |                                     |-- verify tx on Base
  |                                     |-- record payment
  |<-- 200 { result... } ---------------|
```

## Payment verification

In production mode, the middleware:

1. Parses the `X-PAYMENT` header as JSON.
2. Queries the Base (or configured) chain for the transaction.
3. Confirms: correct USDC contract, correct recipient, correct amount, transaction confirmed.
4. Rejects reused tx hashes.
5. Records the payment in `x402_payments`.

In development mode (`X402_MOCK_PAYMENTS=true`), on-chain verification is skipped. This is for local development and tests only. It must never be set in production.

## Premium endpoints

| Endpoint | Price | Function |
|----------|-------|---------|
| `POST /v1/x402/premium/verify-bundle` | 0.001 USDC | Verify an evidence bundle |
| `POST /v1/x402/premium/generate-statement` | 0.005 USDC | Generate a camt.053 statement |
| `POST /v1/x402/premium/fx-lookup` | 0.0005 USDC | Current FX rate (FTSO) |
| `POST /v1/x402/premium/bulk-verify` | 0.01 USDC | Verify multiple bundles |
| `POST /v1/x402/premium/refund` | 0.001 USDC | Initiate a refund |

Prices are configured in the database via `ProtectedEndpoint` records and served by `GET /v1/x402/pricing`.

## Analytics

- `GET /v1/x402/payments` — list verified payments (auth required)
- `GET /v1/x402/revenue?days=7` — revenue summary (admin only)

## Agent auto-anchoring

When an agent has `anchor_on_payment=true`, each verified x402 payment automatically triggers a background anchor task that writes the payment hash to the Flare anchor contract.

## See also

- [Use x402 Paid Endpoints](../guides/use-x402-paid-endpoints.md)
- [API: x402](../api/x402.md)
- [Agentic Workflows](./agentic-workflows.md)
