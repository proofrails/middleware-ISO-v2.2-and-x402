'use client';

interface Props {
  onSwitch: () => void;
}

export function NetworkGate({ onSwitch }: Props) {
  return (
    <div className="card space-y-4">
      <div>
        <p className="label mb-1">Step 2</p>
        <h2 className="text-lg font-semibold text-slate-100">Switch to Flare Coston2</h2>
        <p className="text-sm text-slate-400 mt-1">
          This demo runs on Flare Coston2 (Chain ID 114). Your wallet is on a different network.
        </p>
      </div>

      <div className="bg-navy-800 rounded-lg p-4 border border-navy-700 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Network</span>
          <span className="text-slate-300 font-medium">Flare Coston2</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Chain ID</span>
          <span className="font-mono text-slate-300">114</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">RPC</span>
          <span className="font-mono text-xs text-slate-400 truncate ml-4">
            coston2-api.flare.network
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Native token</span>
          <span className="text-slate-300">C2FLR (testnet)</span>
        </div>
      </div>

      <button onClick={onSwitch} className="btn-primary w-full">
        Switch to Flare Coston2
      </button>

      <p className="text-xs text-slate-600">
        If the switch prompt does not appear, add the network manually using the config above.
      </p>
    </div>
  );
}
