'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';

export function WalletConnectCard() {
  return (
    <div className="card space-y-4">
      <div>
        <p className="label mb-1">Step 1</p>
        <h2 className="text-lg font-semibold text-slate-100">Connect your wallet</h2>
        <p className="text-sm text-slate-400 mt-1">
          Connect an EVM-compatible wallet to begin the Coston2 testnet flow.
        </p>
      </div>

      <div className="bg-navy-800 rounded-lg p-4 text-sm text-slate-400 space-y-1 border border-navy-700">
        <p className="font-medium text-slate-300">Supported wallets</p>
        <p>MetaMask, Coinbase Wallet, WalletConnect-compatible wallets.</p>
      </div>

      <ConnectButton label="Connect wallet" />

      <p className="text-xs text-slate-600">
        Coston2 testnet only. No real funds required.
      </p>
    </div>
  );
}
