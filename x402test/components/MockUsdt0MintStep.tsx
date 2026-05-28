'use client';

import { useState } from 'react';
import { TOKEN_DECIMALS } from '@/lib/contracts';

interface Props {
  tokenBalance: bigint | undefined;
  onMint: () => Promise<void>;
}

function fmt(raw: bigint | undefined, dec = TOKEN_DECIMALS): string {
  if (raw === undefined) return '...';
  const d = BigInt(10 ** dec);
  const whole = raw / d;
  const frac = (raw % d).toString().padStart(dec, '0');
  return `${whole}.${frac}`;
}

export function MockUsdt0MintStep({ tokenBalance, onMint }: Props) {
  const [minting, setMinting] = useState(false);
  const [mintError, setMintError] = useState<string | null>(null);

  async function handleMint() {
    setMinting(true);
    setMintError(null);
    try {
      await onMint();
    } catch (e) {
      setMintError((e as Error).message ?? 'Mint failed');
    } finally {
      setMinting(false);
    }
  }

  return (
    <div className="card space-y-4">
      <div>
        <p className="label mb-1">Step 4</p>
        <h2 className="text-lg font-semibold text-slate-100">Claim MockUSDT0 test credits</h2>
        <p className="text-sm text-slate-400 mt-1">
          MockUSDT0 is a test token that mimics USDT0. You need 0.001 to unlock the brief.
          Minting 1.0 MockUSDT0 gives you plenty.
        </p>
      </div>

      <div className="bg-navy-800 rounded-lg p-4 border border-navy-700 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Your balance</span>
          <span className="font-mono text-slate-300">{fmt(tokenBalance)} MockUSDT0</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Required for payment</span>
          <span className="font-mono text-slate-300">0.001000 MockUSDT0</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Mint amount</span>
          <span className="font-mono text-slate-300">1.000000 MockUSDT0</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Token decimals</span>
          <span className="font-mono text-slate-300">6</span>
        </div>
      </div>

      {mintError && (
        <div className="bg-red-950/50 border border-red-800 rounded-lg p-3 text-sm text-red-400">
          {mintError}
        </div>
      )}

      <button
        onClick={handleMint}
        disabled={minting}
        className="btn-primary w-full"
      >
        {minting ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Minting...
          </span>
        ) : 'Claim MockUSDT0'}
      </button>

      <p className="text-xs text-slate-600">
        MockUSDT0 has no real value. It is used only for this Coston2 testnet demo.
      </p>
    </div>
  );
}
