'use client';

import { useEffect, useState } from 'react';

interface Props {
  paymentId?: string | null;
  verifyUrl?: string | null;
  receiptId?: string | null;
  bundleHash?: string | null;
}

export function VerificationBridge({ paymentId, verifyUrl, receiptId, bundleHash }: Props) {
  const [receipt, setReceipt] = useState({
    verifyUrl: verifyUrl ?? null,
    receiptId: receiptId ?? null,
    bundleHash: bundleHash ?? null,
  });

  useEffect(() => {
    if (!paymentId || receipt.verifyUrl || receipt.receiptId || receipt.bundleHash) return;

    const id = setInterval(async () => {
      try {
        const res = await fetch(`/api/receipt/status/${paymentId}`);
        if (!res.ok) return;
        const data = await res.json() as {
          receipt?: { verify_url?: string | null; receipt_id?: string | null; bundle_hash?: string | null };
        };
        if (data.receipt?.verify_url || data.receipt?.receipt_id || data.receipt?.bundle_hash) {
          setReceipt({
            verifyUrl: data.receipt.verify_url ?? null,
            receiptId: data.receipt.receipt_id ?? null,
            bundleHash: data.receipt.bundle_hash ?? null,
          });
          clearInterval(id);
        }
      } catch {
        // silent; this is a convenience link, not the payment gate
      }
    }, 5000);

    return () => clearInterval(id);
  }, [paymentId, receipt.verifyUrl, receipt.receiptId, receipt.bundleHash]);

  const base = 'https://app.proofrails.com';
  const url = receipt.verifyUrl
    ?? (receipt.receiptId ? `${base}/verify?receipt_id=${encodeURIComponent(receipt.receiptId)}` : null)
    ?? (receipt.bundleHash ? `${base}/verify?bundle_hash=${encodeURIComponent(receipt.bundleHash)}` : `${base}/verify`);
  const ready = !!(receipt.verifyUrl || receipt.receiptId || receipt.bundleHash);

  function handleClick() {
    fetch('/api/analytics', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'verify_clicked' }) }).catch(() => {});
  }

  return (
    <div className="card-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-200">Verify this receipt on ProofRails</p>
        <p className="text-xs text-slate-500 mt-0.5">
          {ready
            ? 'Open the verification interface with the receipt identifier prefilled.'
            : 'Receipt creation is still pending. The verification link will become active once a receipt ID or bundle hash exists.'}
        </p>
      </div>
      {ready ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleClick}
          className="btn-secondary shrink-0 text-sm py-2 px-4 whitespace-nowrap"
        >
          Verify receipt ↗
        </a>
      ) : (
        <button disabled className="btn-secondary shrink-0 text-sm py-2 px-4 whitespace-nowrap opacity-50 cursor-not-allowed">
          Receipt pending
        </button>
      )}
    </div>
  );
}
