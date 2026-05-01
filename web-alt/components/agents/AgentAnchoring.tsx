import { Anchor, HelpCircle, ExternalLink, Check, X, RefreshCw, Loader2 } from "lucide-react";
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
  configLoading: boolean;
  anchors: AnchorRecord[];
  onConfigChange: (patch: Partial<AnchoringConfig>) => void;
  onSaveConfig: () => void;
  onAnchorData: (
    data: object,
    description: string,
    chain: string,
    submitOnchain: boolean,
  ) => Promise<{ anchor_hash?: string; id?: string; status?: string; error?: string } | null>;
  onRefreshAnchors: () => void;
}

const EXPLORER_BASES: Record<string, string> = {
  flare: "https://flare-explorer.flare.network/tx",
  coston2: "https://coston2-explorer.flare.network/tx",
  base: "https://basescan.org/tx",
  sepolia: "https://sepolia.etherscan.io/tx",
};

function explorerUrl(chain: string, txid: string): string | null {
  const base = EXPLORER_BASES[chain.toLowerCase()];
  if (!base || !txid) return null;
  return `${base}/${txid}`;
}

export default function AgentAnchoring({
  agent,
  config,
  configLoading,
  anchors,
  onConfigChange,
  onSaveConfig,
  onAnchorData,
  onRefreshAnchors,
}: AgentAnchoringProps) {
  const [showWalletInput, setShowWalletInput] = useState(false);
  const [walletDraft, setWalletDraft] = useState("");
  const [savingConfig, setSavingConfig] = useState(false);

  // Manual anchor-data form state
  const [anchorJson, setAnchorJson] = useState("");
  const [anchorDescription, setAnchorDescription] = useState("");
  const [anchorChain, setAnchorChain] = useState("flare");
  const [submitOnchain, setSubmitOnchain] = useState(false);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [anchorResult, setAnchorResult] = useState<{ anchor_hash?: string; id?: string; status?: string; error?: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    await onSaveConfig();
    setSavingConfig(false);
  };

  const handleWalletApply = () => {
    if (walletDraft.trim()) {
      onConfigChange({ anchor_wallet: walletDraft.trim() });
    }
    setShowWalletInput(false);
    setWalletDraft("");
  };

  const handleAnchorSubmit = async () => {
    setJsonError(null);
    setAnchorResult(null);

    let parsed: object;
    try {
      parsed = JSON.parse(anchorJson || "{}");
      if (typeof parsed !== "object" || Array.isArray(parsed)) {
        setJsonError("Must be a JSON object, not an array or primitive.");
        return;
      }
    } catch (e: any) {
      setJsonError(`Invalid JSON: ${e.message}`);
      return;
    }

    setSubmitting(true);
    const result = await onAnchorData(parsed, anchorDescription, anchorChain, submitOnchain);
    setAnchorResult(result);
    setSubmitting(false);

    if (result && !result.error) {
      setAnchorJson("");
      setAnchorDescription("");
    }
  };

  return (
    <div className="space-y-4">
      {/* Info */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-purple-900">
            <div className="font-semibold mb-1">On-Chain Anchoring for Agents</div>
            <div>
              Hash arbitrary JSON data and anchor it to the Flare network. The raw data is never stored — only its
              SHA-256 hash. Anchors create an immutable on-chain record that any party can independently verify.
            </div>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Anchor className="h-5 w-5" />
          Anchoring Configuration
          {configLoading && <Loader2 className="h-4 w-4 animate-spin text-slate-400 ml-1" />}
        </h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
            <div>
              <div className="font-semibold">Auto-Anchor Activity</div>
              <div className="text-sm text-slate-600">Automatically anchor important agent events</div>
            </div>
            <button
              onClick={() => onConfigChange({ auto_anchor_enabled: !config.auto_anchor_enabled })}
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

          <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
            <div>
              <div className="font-semibold">Anchor on Payment</div>
              <div className="text-sm text-slate-600">Anchor each verified x402 payment transaction</div>
            </div>
            <button
              onClick={() => onConfigChange({ anchor_on_payment: !config.anchor_on_payment })}
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

          {/* Wallet address */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Anchoring Wallet (optional)</label>
              <button
                onClick={() => {
                  setWalletDraft(config.anchor_wallet || "");
                  setShowWalletInput(!showWalletInput);
                }}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                {showWalletInput ? "Cancel" : config.anchor_wallet ? "Change" : "Configure"}
              </button>
            </div>
            {showWalletInput ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={walletDraft}
                  onChange={(e) => setWalletDraft(e.target.value)}
                  placeholder="0x… (leave empty to use system wallet)"
                  className="flex-1 px-3 py-2 border border-slate-300 rounded text-sm font-mono"
                />
                <button
                  onClick={handleWalletApply}
                  className="px-3 py-2 bg-slate-900 text-white text-sm rounded hover:bg-slate-800"
                >
                  Apply
                </button>
              </div>
            ) : config.anchor_wallet ? (
              <div className="p-3 bg-slate-50 rounded font-mono text-sm break-all">{config.anchor_wallet}</div>
            ) : (
              <div className="text-sm text-slate-500">Using system wallet</div>
            )}
          </div>

          <button
            onClick={handleSaveConfig}
            disabled={savingConfig || configLoading}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {savingConfig && <Loader2 className="h-4 w-4 animate-spin" />}
            Save Anchoring Config
          </button>
        </div>
      </div>

      {/* Manual Anchor Data */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-1">Anchor JSON Data</h3>
        <p className="text-sm text-slate-500 mb-4">
          Hash arbitrary JSON and create an anchor record. Only the hash is stored — raw data is never persisted.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">JSON Data</label>
            <textarea
              value={anchorJson}
              onChange={(e) => {
                setAnchorJson(e.target.value);
                setJsonError(null);
              }}
              placeholder={'{\n  "receipt_id": "...",\n  "event": "payment_verified"\n}'}
              rows={6}
              className={`w-full px-3 py-2 border rounded text-sm font-mono resize-y ${
                jsonError ? "border-red-400 bg-red-50" : "border-slate-300"
              }`}
            />
            {jsonError && <p className="text-xs text-red-600 mt-1">{jsonError}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description (optional)</label>
            <input
              type="text"
              value={anchorDescription}
              onChange={(e) => setAnchorDescription(e.target.value)}
              placeholder="e.g. Payment proof for receipt abc123"
              className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
            />
          </div>

          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Chain</label>
              <select
                value={anchorChain}
                onChange={(e) => setAnchorChain(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
              >
                <option value="flare">Flare</option>
                <option value="coston2">Coston2 (testnet)</option>
                <option value="base">Base</option>
                <option value="sepolia">Sepolia (testnet)</option>
              </select>
            </div>

            <div className="flex items-center gap-2 pt-5">
              <button
                onClick={() => setSubmitOnchain(!submitOnchain)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  submitOnchain ? "bg-blue-600" : "bg-slate-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    submitOnchain ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
              <label className="text-sm font-medium whitespace-nowrap">Submit on-chain</label>
            </div>
          </div>

          {submitOnchain && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
              On-chain submission requires a configured anchoring wallet or{" "}
              <code>ANCHOR_PRIVATE_KEY</code> on the server. Hash will be recorded pending if no key
              is available.
            </div>
          )}

          {anchorResult && (
            <div
              className={`rounded p-3 text-sm ${
                anchorResult.error
                  ? "bg-red-50 border border-red-200 text-red-800"
                  : "bg-green-50 border border-green-200 text-green-800"
              }`}
            >
              {anchorResult.error ? (
                <span>Error: {anchorResult.error}</span>
              ) : (
                <div className="space-y-1">
                  <div className="font-medium">Anchor created</div>
                  {anchorResult.anchor_hash && (
                    <div className="font-mono text-xs break-all">Hash: {anchorResult.anchor_hash}</div>
                  )}
                  <div>Status: {anchorResult.status}</div>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleAnchorSubmit}
            disabled={submitting}
            className="w-full px-4 py-2 bg-slate-900 text-white rounded hover:bg-slate-800 disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitOnchain ? "Hash and Anchor On-Chain" : "Hash and Record Locally"}
          </button>
        </div>
      </div>

      {/* Anchor History */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">Anchor History</h3>
          <button
            onClick={onRefreshAnchors}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </button>
        </div>

        {anchors.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No anchors yet for this agent.
          </div>
        ) : (
          <div className="space-y-3">
            {anchors.map((anchor) => {
              const txUrl = anchor.anchor_txid ? explorerUrl(anchor.chain, anchor.anchor_txid) : null;
              return (
                <div key={anchor.id} className="flex gap-3 p-3 bg-slate-50 rounded">
                  <Anchor className="h-5 w-5 text-purple-600 flex-shrink-0 mt-1" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-mono truncate" title={anchor.bundle_hash}>
                      {anchor.bundle_hash}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span
                        className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${
                          anchor.status === "confirmed"
                            ? "bg-green-100 text-green-800"
                            : anchor.status === "pending"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {anchor.status === "confirmed" && <Check className="h-3 w-3" />}
                        {anchor.status === "failed" && <X className="h-3 w-3" />}
                        {anchor.status}
                      </span>
                      <span className="text-xs text-slate-500">{anchor.chain}</span>
                      {anchor.anchored_at && (
                        <span className="text-xs text-slate-400">
                          {new Date(anchor.anchored_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                    {txUrl && (
                      <a
                        href={txUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 mt-1"
                      >
                        View on explorer
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
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
            {anchors.filter((a) => a.status === "confirmed").length}
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm text-slate-600">Pending</div>
          <div className="text-2xl font-bold text-yellow-600">
            {anchors.filter((a) => a.status === "pending").length}
          </div>
        </div>
      </div>
    </div>
  );
}
