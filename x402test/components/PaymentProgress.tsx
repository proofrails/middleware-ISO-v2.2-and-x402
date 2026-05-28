'use client';

import clsx from 'clsx';
import type { ProcessingSubstep } from '@/hooks/useUnlockFlow';
import { EXPLORER_TX_URL } from '@/lib/chains';

interface Props {
  substep: ProcessingSubstep | null;
  txHash: string | null;
}

const SUBSTEPS: { id: ProcessingSubstep; label: string; detail: string }[] = [
  { id: 'verifying', label: 'Checking payment validity', detail: 'Calling facilitator precheck...' },
  { id: 'settling', label: 'Waiting for wallet confirmation', detail: 'Confirm the transaction in your wallet.' },
  { id: 'confirming', label: 'Waiting for Coston2 settlement', detail: 'Transaction submitted. Waiting for block confirmation...' },
  { id: 'unlocking', label: 'Unlocking research brief', detail: 'Verifying settlement on-chain...' },
  { id: 'receipt', label: 'Creating ProofRails receipt', detail: 'Recording the payment event...' },
];

const ORDER: ProcessingSubstep[] = ['verifying', 'settling', 'confirming', 'unlocking', 'receipt'];

export function PaymentProgress({ substep, txHash }: Props) {
  const currentIdx = substep ? ORDER.indexOf(substep) : 0;
  const current = SUBSTEPS.find(s => s.id === substep);

  return (
    <div className="card space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Processing payment</h2>
        <p className="text-sm text-slate-400 mt-1">
          {current?.detail ?? 'Preparing payment payload...'}
        </p>
      </div>

      <div className="space-y-3">
        {SUBSTEPS.map((s, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          return (
            <div key={s.id} className={clsx(
              'flex items-center gap-3 py-2 px-3 rounded-lg transition-colors',
              active && 'bg-navy-800 border border-navy-600',
            )}>
              <div className={clsx(
                'w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs',
                done && 'bg-green-500 text-white',
                active && 'border-2 border-accent',
                !done && !active && 'border border-navy-600',
              )}>
                {done ? '✓' : active ? (
                  <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                ) : null}
              </div>
              <span className={clsx(
                'text-sm',
                active && 'text-slate-100 font-medium',
                done && 'text-green-400',
                !done && !active && 'text-slate-600',
              )}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {txHash && (
        <div className="space-y-1">
          <p className="label">Settlement transaction</p>
          <a
            href={EXPLORER_TX_URL(txHash)}
            target="_blank"
            rel="noopener noreferrer"
            className="hash-pill block hover:text-slate-200 transition-colors"
          >
            {txHash}
          </a>
        </div>
      )}
    </div>
  );
}
