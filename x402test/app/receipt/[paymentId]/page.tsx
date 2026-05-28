import { findByPaymentId } from '@/lib/unlocks';
import { EXPLORER_TX_URL } from '@/lib/chains';
import Link from 'next/link';

interface Props {
  params: { paymentId: string };
}

export default function ReceiptPage({ params }: Props) {
  const record = findByPaymentId(params.paymentId);

  if (!record) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
        <h1 className="text-2xl font-bold text-slate-100">Receipt not found</h1>
        <p className="text-slate-400">No payment record found for this ID.</p>
        <Link href="/" className="btn-secondary inline-block">Back to home</Link>
      </div>
    );
  }

  const fields = [
    { label: 'Payment ID', value: record.payment_id, mono: true },
    { label: 'Settlement tx', value: record.settlement_tx_hash, mono: true, link: EXPLORER_TX_URL(record.settlement_tx_hash) },
    { label: 'Network', value: `Flare Coston2 (chain ${record.chain_id})` },
    { label: 'Token', value: 'MockUSDT0' },
    { label: 'Amount', value: `${(Number(record.amount_raw) / 1_000_000).toFixed(6)} MockUSDT0` },
    { label: 'Payer', value: record.wallet_address, mono: true },
    { label: 'Recipient', value: record.recipient, mono: true },
    { label: 'Resource', value: record.resource_id },
    { label: 'Status', value: record.status },
    { label: 'Settled at', value: record.created_at },
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 py-16 space-y-8">
      <div className="space-y-2">
        <p className="label">ProofRails receipt</p>
        <h1 className="text-2xl font-bold text-slate-100">Payment record</h1>
        <p className="text-slate-400 text-sm">
          A verifiable record of the payment event that unlocked the Flare x ProofRails research brief.
        </p>
      </div>

      <div className="card divide-y divide-navy-700 p-0 overflow-hidden">
        {fields.map(({ label, value, mono, link }) => (
          <div key={label} className="flex flex-col sm:flex-row sm:justify-between px-5 py-3 gap-1">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider shrink-0">{label}</span>
            {link ? (
              <a href={link} target="_blank" rel="noopener noreferrer"
                className={`text-sm text-blue-400 hover:text-blue-300 break-all ${mono ? 'font-mono' : ''}`}>
                {value} ↗
              </a>
            ) : (
              <span className={`text-sm text-slate-300 break-all ${mono ? 'font-mono' : ''}`}>{value}</span>
            )}
          </div>
        ))}
      </div>

      {(record.receipt_id || record.bundle_hash) && (
        <div className="card space-y-3">
          <p className="label">ProofRails evidence</p>
          {record.receipt_id && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Receipt ID</p>
              <p className="hash-pill">{record.receipt_id}</p>
            </div>
          )}
          {record.bundle_hash && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Bundle hash</p>
              <p className="hash-pill">{record.bundle_hash}</p>
            </div>
          )}
          {record.verify_url && (
            <a href={record.verify_url} target="_blank" rel="noopener noreferrer"
              className="btn-secondary inline-block text-sm">
              Verify receipt ↗
            </a>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Link href="/" className="btn-secondary">Back to home</Link>
        <a href="https://app.proofrails.com/verify" target="_blank" rel="noopener noreferrer"
          className="btn-ghost">
          Verify on ProofRails ↗
        </a>
      </div>
    </div>
  );
}
