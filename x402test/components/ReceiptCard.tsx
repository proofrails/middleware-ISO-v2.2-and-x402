'use client';

import { useState, useEffect } from 'react';
import clsx from 'clsx';

interface ReceiptStatus {
  status: string;
  receipt_id: string | null;
  bundle_hash: string | null;
  verify_url: string | null;
}

interface Props {
  paymentId: string | null;
  initialReceipt: { status: string; receipt_id: string | null; bundle_hash?: string | null; verify_url: string | null };
}

export function ReceiptCard({ paymentId, initialReceipt }: Props) {
  const [receipt, setReceipt] = useState<ReceiptStatus>({
    status: initialReceipt.status,
    receipt_id: initialReceipt.receipt_id,
    bundle_hash: initialReceipt.bundle_hash ?? null,
    verify_url: initialReceipt.verify_url,
  });
  const [polling, setPolling] = useState(receipt.status === 'pending_creation');

  useEffect(() => {
    if (!polling || !paymentId) return;
    const id = setInterval(async () => {
      try {
        const res = await fetch(`/api/receipt/status/${paymentId}`);
        if (!res.ok) return;
        const data = await res.json() as { receipt: ReceiptStatus };
        setReceipt(data.receipt);
        if (data.receipt.status === 'created') {
          setPolling(false);
          clearInterval(id);
        }
      } catch {
        // silent
      }
    }, 5000);
    return () => clearInterval(id);
  }, [polling, paymentId]);

  const isPending = receipt.status === 'pending_creation' || receipt.status === 'pending';

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="label mb-1">ProofRails receipt</p>
          <h3 className="font-medium text-slate-100">Payment evidence record</h3>
        </div>
        <div className={clsx(
          'flex items-center gap-2 text-xs font-medium px-2.5 py-1 rounded-full border',
          isPending
            ? 'bg-amber-950/30 border-amber-800/50 text-amber-400'
            : 'bg-green-950/30 border-green-800/50 text-green-400',
        )}>
          <span className={clsx('status-dot', isPending ? 'bg-amber-400 animate-pulse' : 'bg-green-400')} />
          {isPending ? 'Creating...' : 'Created'}
        </div>
      </div>

      <p className="text-sm text-slate-400">
        This receipt records the payment event that unlocked the resource. It links the payer,
        recipient, token, amount, settlement transaction, and ProofRails evidence trail.
      </p>

      {receipt.receipt_id && (
        <div className="space-y-1">
          <p className="label">Receipt ID</p>
          <p className="hash-pill">{receipt.receipt_id}</p>
        </div>
      )}

      {receipt.bundle_hash && (
        <div className="space-y-1">
          <p className="label">Bundle hash</p>
          <p className="hash-pill">{receipt.bundle_hash}</p>
        </div>
      )}

      {isPending && (
        <p className="text-xs text-slate-600">
          Receipt creation runs in the background. This page will update automatically.
        </p>
      )}
    </div>
  );
}
