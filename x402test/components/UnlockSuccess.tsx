'use client';

import type { UnlockResult } from '@/hooks/useUnlockFlow';
import { EXPLORER_TX_URL } from '@/lib/chains';

interface Props {
  result: UnlockResult;
  txHash: string | null;
}

export function UnlockSuccess({ result, txHash }: Props) {
  return (
    <div className="space-y-5">
      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center text-green-400 text-lg">
            ✓
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Unlocked</h2>
            <p className="text-sm text-slate-400">
              Your x402 payment was verified and the research brief is ready.
            </p>
          </div>
        </div>

        <div className="bg-navy-800 rounded-lg border border-navy-700 p-4">
          <p className="text-sm font-medium text-slate-200 mb-1">{result.resource.title}</p>
          <p className="text-xs text-slate-500 mb-4">
            Access expires in 24 hours. Download now to keep a copy.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <a
              href={result.resource.pdf_url}
              className="btn-primary flex-1 text-center text-sm py-2.5"
            >
              Download PDF
            </a>
            <a
              href={result.resource.markdown_url}
              className="btn-secondary flex-1 text-center text-sm py-2.5"
            >
              Download Markdown
            </a>
            <a
              href={result.resource.web_url}
              className="btn-ghost flex-1 text-center text-sm py-2.5"
            >
              Read online
            </a>
          </div>
        </div>
      </div>

      {txHash && (
        <div className="card-sm space-y-2">
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
