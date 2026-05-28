'use client';

import { FACILITATOR_ADDRESS, RECIPIENT_ADDRESS, MOCK_USDT0_ADDRESS } from '@/lib/contracts';

interface Props {
  address: string;
  onPay: () => void;
}

function truncate(addr: string) {
  return `${addr.slice(0, 8)}…${addr.slice(-6)}`;
}

export function PaymentSummary({ address, onPay }: Props) {
  return (
    <div className="card space-y-5">
      <div>
        <p className="label mb-1">Step 5</p>
        <h2 className="text-lg font-semibold text-slate-100">Confirm x402 payment</h2>
        <p className="text-sm text-slate-400 mt-1">
          Review the payment details below. Your wallet will ask for confirmation.
        </p>
      </div>

      <div className="bg-navy-800 rounded-lg border border-navy-700 divide-y divide-navy-700 text-sm">
        {[
          { label: 'You are paying', value: '0.001 MockUSDT0' },
          { label: 'Network', value: 'Flare Coston2' },
          { label: 'Purpose', value: 'Unlock the Flare x ProofRails research brief' },
          { label: 'From', value: truncate(address) },
          { label: 'Recipient', value: truncate(RECIPIENT_ADDRESS) },
          { label: 'Token', value: `MockUSDT0 (${truncate(MOCK_USDT0_ADDRESS)})` },
          { label: 'Facilitator', value: truncate(FACILITATOR_ADDRESS) },
          { label: 'Amount (raw)', value: '1000 units (6 decimals)' },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between px-4 py-3">
            <span className="text-slate-500">{label}</span>
            <span className="text-slate-200 font-medium text-right ml-4 max-w-[60%] break-all">{value}</span>
          </div>
        ))}
      </div>

      <div className="bg-amber-950/30 border border-amber-900/50 rounded-lg p-3 text-xs text-amber-400">
        Coston2 testnet only. MockUSDT0 has no real value.
        The current mock token does not enforce EIP-712 signatures.
      </div>

      <button onClick={onPay} className="btn-primary w-full text-base py-3.5">
        Pay 0.001 MockUSDT0
      </button>
    </div>
  );
}
