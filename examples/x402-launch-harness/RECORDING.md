# Launch video recording plan

Live terminal recording of one real run. No mockups, no animation, no spliced
transactions. Target length 75–100 seconds, 16:9, 2560x1440.

## Environment

- Display set to 2560x1440 before recording.
- Dedicated clean terminal profile: large font, no shell history, no personal
  folders, no notifications, no credentials or environment dumps on screen.
- Secrets are exported in a separate non-recorded shell step; the harness never
  prints keys, signatures, or environment values.

## Shots

| Time    | Content                                                                                                                                                                                                                                                                                                                                                                    |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0–7s    | ProofRails docs homepage for ~2s, then terminal. Title: `A paid API call, with the receipt built in.` Subline: `x402 payment · delivered result · signed evidence · Flare anchor`                                                                                                                                                                                          |
| 7–20s   | `node harness.mjs preflight` — request, 402, network, asset, amount, pay-to, facilitator. Caption: `The API declares the exact payment terms before authorization.`                                                                                                                                                                                                        |
| 20–42s  | `node harness.mjs record` — `PAYMENT-SIGNATURE created locally`, `SETTLEMENT confirmed on Flare mainnet`, `RETRY same endpoint`, `RESOURCE 200 OK`, `PAYMENT-RESPONSE received`, delivered `rate`/`source`, then `settlement_tx`, `receipt_id`, `receipt_url`, `verifier_url`, `resource_hash`. Caption: `Payment and delivery now share one traceable receipt reference.` |
| 42–68s  | Real receipt lifecycle states, delivery hash, artifacts actually present, `evidence.zip`, signature, anchor status.                                                                                                                                                                                                                                                        |
| 68–88s  | Independent verification table produced by `verify`.                                                                                                                                                                                                                                                                                                                       |
| 88–100s | Public receipt/verifier page from this exact run. Closing: `ProofRails` / `Verifiable receipts for onchain payments and paid API calls.` / `Settlement is only the beginning of the record.` / `proofrails.com`                                                                                                                                                            |

A persistent label `FLARE MAINNET · REAL VALUE · 0.001 USD₮0` is burned in over the
payment sequence.

## Editing

Waiting time may be shortened, but the payment-to-evidence sequence stays
continuous and comes from a single transaction and receipt.

```bash
./edit.sh raw.mp4 final.mp4
```

`edit.sh` only adds titles, captions and the persistent mainnet label, and
optionally trims dead waiting time between the timestamps listed in the run log.
It never re-orders or substitutes output.

## Language rules

- Use `ISO 20022-style artifacts`.
- Never say compliant, certified, bank-grade, audit-ready, production-ready or
  enterprise-ready.
- If facilitator wording appears: ProofRails operates an integrated x402
  facilitator for its own payment-gated APIs; on Flare, USDT0 settlement uses the
  ProofRails X402Facilitator contract.
- An onchain anchor proves integrity and timing of the committed hash, not the
  truth or legal sufficiency of offchain data.

## Failure rules

- If the official client does not complete 402 → payment → 200 on the same
  endpoint, stop. Never substitute a bespoke payment header.
- After a broadcast, never send a second payment because delivery, receipt,
  bundle, anchor or recording failed.
- If settlement succeeds and a later stage fails, keep the footage, mark the run
  failed and report the exact stage.
- If the current bundle hash does not equal the anchored hash, do not show
  `verified` or `PASS`.
