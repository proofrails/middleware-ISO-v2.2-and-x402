import { Anchor, HelpCircle, ExternalLink, Check, X } from "lucide-react";
import { useState } from "react";

interface Agent {
  id: string;
  name: string;
}

interface AnchoringConfig {
  auto_anchor_enabled: boolean;
  anchor_on_payment: boolean;
  anchor_wallet?: string;
}

interface AnchorRecord {
  id: string;
  bundle_hash: string;
  anchor_txid: string | null;
  chain: string;
  status: string;
  anchored_at: string | null;
  created_at: string;
}

interface AgentAnchoringProps {
  agent: Agent;
  config: AnchoringConfig;
  anchors: AnchorRecord[];
  onConfigChange: (config: AnchoringConfig) => void;
  onSaveConfig: () => void;
  API_BASE: string;
}

export default function AgentAnchoring({
  agent,
  config,
  anchors,
  onConfigChange,
  onSaveConfig,
  API_BASE,
}: AgentAnchoringProps) {
  const [showWalletInput, setShowWalletInput] = useState(false);

  return (
    <div className="space-y-4">
      {/* Info Box */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-purple-900">
            <div className="font-semibold mb-1">On-Chain Anchoring for Agents</div>
            <div>Enable automatic anchoring of agent activity to Flare network for cryptographic proof and immutability. Each anchor creates an on-chain record that can be independently verified.</div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Anchor className="h-5 w-5" />
          Anchoring Configuration
        </h3>
        
        <div className="space-y-4">
          {/* Auto-anchor toggle */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
            <div>
              <div className="font-semibold">Auto-Anchor Activity</div>
              <div className="text-sm text-slate-600">Automatically anchor important agent events</div>
            </div>
            <button
              onClick={() => onConfigChange({ ...config, auto_anchor_enabled: !config.auto_anchor_enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.auto_anchor_enabled ? "bg-blue-600" : "bg-slate-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.auto_anchor_enabled ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Anchor on payment */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
            <div>
              <div className="font-semibold">Anchor on Payment</div>
              <div className="text-sm text-slate-600">Anchor every x402 payment transaction</div>
            </div>
            <button
              onClick={() => onConfigChange({ ...config, anchor_on_payment: !config.anchor_on_payment })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.anchor_on_payment ? "bg-blue-600" : "bg-slate-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.anchor_on_payment ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Anchor wallet */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Anchoring Wallet (Optional)</label>
              <button
                onClick={() => setShowWalletInput(!showWalletInput)}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                {showWalletInput ? "Cancel" : config.anchor_wallet ? "Change" : "Configure"}
              </button>
            </div>
            {config.anchor_wallet && !showWalletInput ? (
              <div className="p-3 bg-slate-50 rounded font-mono text-sm">
                {config.anchor_wallet}
              </div>
            ) : showWalletInput ? (
              <input
                type="text"
                placeholder="0x... (leave empty to use system wallet)"
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                onBlur={(e) => {
                  if (e.target.value) {
                    onConfigChange({ ...config, anchor_wallet: e.target.value });
                  }
                  setShowWalletInput(false);
                }}
              />
            ) : (
              <div className="text-sm text-slate-500">Using system wallet</div>
            )}
          </div>

          <button
            onClick={onSaveConfig}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            Save Anchoring Config
          </button>
        </div>
      </div>

      {/* Anchor History */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4">Anchor History</h3>
        
        {anchors.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No anchors yet. Enable auto-anchoring or manually trigger anchors.
          </div>
        ) : (
          <div className="space-y-3">
            {anchors.map((anchor) => (
              <div key={anchor.id} className="flex gap-3 p-3 bg-slate-50 rounded">
                <Anchor className="h-5 w-5 text-purple-600 flex-shrink-0 mt-1" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono truncate">{anchor.bundle_hash}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      anchor.status === "confirmed" 
                        ? "bg-green-100 text-green-800"
                        : anchor.status === "pending"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-red-100 text-red-800"
                    }`}>
                      {anchor.status === "confirmed" && <Check className="inline h-3 w-3 mr-1" />}
                      {anchor.status === "failed" && <X className="inline h-3 w-3 mr-1" />}
                      {anchor.status}
                    </span>
                    <span className="text-xs text-slate-500">{anchor.chain}</span>
                    {anchor.anchored_at && (
                      <span className="text-xs text-slate-500">
                        {new Date(anchor.anchored_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {anchor.anchor_txid && (
                    <a
                      href={`https://flare-explorer.flare.network/tx/${anchor.anchor_txid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 mt-1"
                    >
                      View on Flare
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm text-slate-600">Total Anchors</div>
          <div className="text-2xl font-bold">{anchors.length}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm text-slate-600">Confirmed</div>
          <div className="text-2xl font-bold text-green-600">
            {anchors.filter(a => a.status === "confirmed").length}
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm text-slate-600">Pending</div>
          <div className="text-2xl font-bold text-yellow-600">
            {anchors.filter(a => a.status === "pending").length}
          </div>
        </div>
      </div>
    </div>
  );
}
