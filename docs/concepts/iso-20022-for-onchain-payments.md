# ISO 20022 for On-Chain Payments

## The standard

ISO 20022 defines a common XML syntax and a library of message types for financial messaging. The relevant message families are:

| Message | Type | Purpose |
|---------|------|---------|
| pain.001 | CustomerCreditTransferInitiation | Initiation of a payment instruction |
| pain.002 | CustomerPaymentStatusReport | Status update for a payment |
| pain.008 | CustomerDirectDebitInitiation | Direct debit initiation |
| pacs.008 | FIToFICustomerCreditTransfer | Settlement between institutions |
| pacs.004 | PaymentReturn | Return of funds |
| camt.053 | BankToCustomerStatement | End-of-day account statement |
| camt.054 | BankToCustomerDebitCreditNotification | Individual debit/credit notification |
| camt.052 | BankToCustomerAccountReport | Intraday account report |
| remt.001 | RemittanceAdvice | Remittance information |

## Mapping on-chain data to ISO messages

A Flare C-Chain transaction carries:

- `from` → `sender_wallet` → `<Dbtr><Id>` (debtor)
- `to` → `receiver_wallet` → `<Cdtr><Id>` (creditor)
- `value` (in Wei) → converted to ISO decimal amount
- `blockTimestamp` → `<CreDtTm>`, `<IntrBkSttlmDt>`
- `transactionHash` → `<EndToEndId>`, `<TxId>` (used as unique reference)
- `chainId` + `blockNumber` → evidence metadata

ProofRails generates pain.001 at initiation, pacs.008 at settlement confirmation, and camt.053/camt.054 for statement periods.

## Limitations of the mapping

On-chain transactions do not carry:

- Real-world debtor/creditor legal names or BICs — ProofRails uses wallet addresses.
- Purpose codes in the traditional sense — `OTHR` is used unless the project configures a mapping.
- Regulated LEIs — the fields are populated with wallet addresses or left empty.
- Netting or batching — each transaction produces its own message set.

These limitations are documented in the generated XML as custom extension elements and must be disclosed to any party relying on the output for regulatory purposes.

## Supported chains

| Chain | Status |
|-------|--------|
| Flare C-Chain (mainnet) | Implemented |
| Coston2 (Flare testnet) | Implemented |
| Base (mainnet/Sepolia) | Partial — x402 payment chain only |

## See also

- [Evidence Bundles](./evidence-bundles.md)
- [API: Receipts](../api/receipts.md)
- [Architecture: Receipt Lifecycle](../architecture/receipt-lifecycle.md)
