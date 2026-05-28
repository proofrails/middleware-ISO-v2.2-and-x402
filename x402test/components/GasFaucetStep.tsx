'use client';

import { FAUCET_URL } from '@/lib/chains';
import { useEffect, useState } from 'react';

interface Props {
  hasGas: boolean;
}

export function GasFaucetStep({ hasGas }: Props) {
  const [opened, setOpened] = useState(false);

  useEffect(() => {
    if (hasGas) return;
  }, [hasGas]);

  function openFaucet() {
    setOpened(true);
    window.open(FAUCET_URL, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="card space-y-4">
      <div>
        <p className="label mb-1">Step 3</p>
        <h2 className="text-lg font-semibold text-slate-100">Get C2FLR for testnet gas</h2>
        <p className="text-sm text-slate-400 mt-1">
          You need a small amount of C2FLR to pay for Coston2 transaction fees.
          C2FLR has no real value.
        </p>
      </div>

      <div className="bg-navy-800 rounded-lg p-4 border border-navy-700 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Required</span>
          <span className="font-mono text-slate-300">&gt; 0.01 C2FLR</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Faucet</span>
          <span className="text-slate-400 text-xs">faucet.flare.network/coston2</span>
        </div>
      </div>

      {!opened ? (
        <button onClick={openFaucet} className="btn-primary w-full">
          Open Coston2 Faucet
        </button>
      ) : (
        <div className="space-y-3">
          <div className="bg-navy-800 border border-navy-600 rounded-lg p-3 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <span className="status-dot bg-amber-400 animate-pulse-slow" />
              Checking your C2FLR balance every 5 seconds...
            </div>
          </div>
          <button onClick={openFaucet} className="btn-secondary w-full text-sm">
            Open faucet again
          </button>
        </div>
      )}

      <p className="text-xs text-slate-600">
        The faucet uses reCAPTCHA. Complete it in the new tab, then return here.
        Your balance is checked automatically.
      </p>
    </div>
  );
}
