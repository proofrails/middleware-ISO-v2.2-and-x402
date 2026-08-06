'use client';

interface Props {
  error: string;
  txHash?: string | null;
  onRetry: () => void;
}

const KNOWN_ERRORS: Record<string, string> = {
  'User rejected': 'Payment was cancelled in your wallet. No resource was unlocked.',
  'rejected': 'Payment was cancelled in your wallet. No resource was unlocked.',
  'Payment payload rejected': 'The facilitator rejected this payment payload. A new payment payload will be generated on retry.',
  'Transaction not found': 'The settlement transaction was not found on Coston2. Check the explorer or try again.',
  'nonce': 'A nonce conflict was detected. Retrying will generate a fresh payment payload.',
};

function friendlyMessage(raw: string): string {
  for (const [key, msg] of Object.entries(KNOWN_ERRORS)) {
    if (raw.toLowerCase().includes(key.toLowerCase())) return msg;
  }
  return raw;
}

export function ErrorRecovery({ error, txHash, onRetry }: Props) {
  return (
    <div className="card space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-red-950/50 border border-red-800/50 flex items-center justify-center text-red-400 shrink-0 mt-0.5">
          !
        </div>
        <div>
          <h2 className="font-semibold text-slate-100">Something went wrong</h2>
          <p className="text-sm text-slate-400 mt-1">{friendlyMessage(error)}</p>
        </div>
      </div>

      {txHash && (
        <div className="space-y-1">
          <p className="label">Transaction hash (if available)</p>
          <a
            href={`https://coston2-explorer.flare.network/tx/${txHash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="hash-pill block hover:text-slate-200 transition-colors"
          >
            {txHash}
          </a>
          <p className="text-xs text-slate-600">
            If payment settled, contact support with this tx hash to recover access.
          </p>
        </div>
      )}

      <button onClick={onRetry} className="btn-primary w-full">
        Try again
      </button>
    </div>
  );
}
