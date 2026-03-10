"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Factory, Save, Rocket, RefreshCcw } from "lucide-react";
import { BrowserProvider, Contract } from "ethers";
import { useProjectStore } from "../lib/client/useProjectStore";
import { detectEthereumProvider } from "../lib/client/ethereum";

type ProjectAnchoringChain = {
  name: string;
  contract: string;
  rpc_url?: string | null;
  explorer_base_url?: string | null;
};
type ProjectConfig = { anchoring: { execution_mode: "platform" | "tenant"; chains: ProjectAnchoringChain[] } };

type DeployResult = { factory: string; anchor: string; txHash: string };

const FACTORY_ABI = [
  {
    type: "event",
    name: "AnchorDeployed",
    inputs: [
      { indexed: true, name: "owner", type: "address" },
      { indexed: false, name: "anchor", type: "address" },
      { indexed: false, name: "ts", type: "uint256" },
    ],
  },
  {
    type: "function",
    name: "deploy",
    stateMutability: "nonpayable",
    inputs: [],
    outputs: [{ name: "anchor", type: "address" }],
  },
] as const;

function defaultConfig(): ProjectConfig {
  return { anchoring: { execution_mode: "platform", chains: [] } };
}

export default function ProjectConfigPanel() {
  const { activeProject, loading: projectLoading } = useProjectStore();

  const [cfg, setCfg] = useState<ProjectConfig>(defaultConfig());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Deploy UI state
  const [factoryAddr, setFactoryAddr] = useState<string>(process.env.NEXT_PUBLIC_ANCHOR_FACTORY_ADDR || "");
  const [chainName, setChainName] = useState<string>("flare");
  const [rpcUrl, setRpcUrl] = useState<string>("");
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<DeployResult | null>(null);

  const defaultExplorerBaseUrl = useMemo(() => {
    if (chainName.trim().toLowerCase() === "flare") return "https://flarescan.com";
    return null;
  }, [chainName]);

  const canUse = useMemo(() => !projectLoading && !!activeProject?.id, [projectLoading, activeProject]);

  async function load() {
    if (!canUse) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    setDeployResult(null);
    try {
      const r = await fetch(`/api/proxy/v1/projects/${activeProject!.id}/config`, { cache: "no-store" });
      const txt = await r.text().catch(() => "");
      if (!r.ok) throw new Error(`load_project_config_failed:${r.status}:${txt}`);
      const data = JSON.parse(txt) as ProjectConfig;
      setCfg({ ...defaultConfig(), ...(data || {}) });
    } catch (e: any) {
      setError(String(e?.message || e));
      setCfg(defaultConfig());
    } finally {
      setLoading(false);
    }
  }

  async function save(next: ProjectConfig = cfg) {
    if (!canUse) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const r = await fetch(`/api/proxy/v1/projects/${activeProject!.id}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const txt = await r.text().catch(() => "");
      if (!r.ok) throw new Error(`save_project_config_failed:${r.status}:${txt}`);
      const data = JSON.parse(txt) as ProjectConfig;
      setCfg({ ...defaultConfig(), ...(data || {}) });
      setMessage("Project config saved.");
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    load().catch(() => void 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canUse]);

  async function deployWithMetaMask() {
    setDeployResult(null);
    setMessage(null);
    setError(null);

    if (!factoryAddr || !factoryAddr.startsWith("0x") || factoryAddr.length !== 42) {
      setError("Provide a valid factory address (0x...).");
      return;
    }

    const eth = await detectEthereumProvider({ timeoutMs: 2500, preferMetaMask: true });
    if (!eth) {
      setError(
        "No wallet found (EIP-1193 provider missing). Make sure MetaMask is installed/enabled for this site. " +
          "If you're using Brave, check Settings → Wallet → Default wallet (MetaMask) and reload."
      );
      return;
    }

    setDeploying(true);
    try {
      try {
        await eth.request?.({ method: "eth_requestAccounts" });
      } catch {
        // ignore
      }
      const provider = new BrowserProvider(eth);
      const signer = await provider.getSigner();

      const contract = new Contract(factoryAddr, FACTORY_ABI as any, signer);
      const tx = await contract.deploy();
      const receipt = await tx.wait();

      // Parse AnchorDeployed event to get new contract address.
      let anchorAddr: string | null = null;
      try {
        for (const log of receipt.logs || []) {
          try {
            const parsed = contract.interface.parseLog(log);
            if (parsed?.name === "AnchorDeployed") {
              anchorAddr = String(parsed.args.anchor);
              break;
            }
          } catch {
            // ignore non-matching log
          }
        }
      } catch {
        // ignore
      }

      // Fallback: if ABI returns anchor as function output (some RPCs support it)
      if (!anchorAddr) {
        // last resort: just tell user to inspect tx
        throw new Error("Could not parse AnchorDeployed event to extract deployed address.");
      }

      const out: DeployResult = {
        factory: factoryAddr,
        anchor: anchorAddr,
        txHash: tx.hash,
      };
      setDeployResult(out);

      // Update project config: set tenant mode, and set chain contract.
      const next: ProjectConfig = {
        ...cfg,
        anchoring: {
          execution_mode: "tenant",
          chains: upsertChain(cfg.anchoring?.chains || [], {
            name: chainName.trim() || "flare",
            contract: anchorAddr,
            rpc_url: rpcUrl.trim() || null,
            explorer_base_url: defaultExplorerBaseUrl,
          }),
        },
      };
      setCfg(next);

      if (canUse) {
        await save(next);
        setMessage("Deployed EvidenceAnchor and saved into project config.");
      } else {
        setMessage("Deployed EvidenceAnchor. Select/register a project to save this address into project config.");
      }
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setDeploying(false);
    }
  }

  function upsertChain(chains: ProjectAnchoringChain[], c: ProjectAnchoringChain): ProjectAnchoringChain[] {
    const idx = chains.findIndex((x) => x.name === c.name);
    const out = chains.slice();
    if (idx >= 0) out[idx] = c;
    else out.push(c);
    return out;
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold flex items-center gap-2">
            <Factory className="h-4 w-4" /> Project Config
          </div>
          <div className="text-xs text-slate-600">Per-project anchoring settings and on-chain deployment</div>
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
            onClick={load}
            disabled={!canUse || loading}
            title="Refresh"
          >
            <RefreshCcw className="h-4 w-4 mr-2" /> {loading ? "Loading…" : "Refresh"}
          </button>
          <button
            className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
            onClick={() => save()}
            disabled={!canUse || saving}
            title="Save config"
          >
            <Save className="h-4 w-4 mr-2" /> {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      {!canUse && (
        <div className="text-sm text-slate-600">
          Select or register a project to edit and save project config.
          <div className="mt-1 text-xs text-slate-500">
            You can still deploy a contract below, but saving the deployed address into config requires an active project.
          </div>
        </div>
      )}

      {/*
        Keep the deploy section always visible so it's discoverable.
        We disable actions that require a project (saving config).
      */}
      <div className="space-y-3">
        <div className="rounded border p-3 bg-white/60 space-y-2">
          <div className="text-sm font-medium">Anchoring mode</div>
          <label className="text-xs text-slate-600">execution_mode</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={cfg.anchoring.execution_mode}
            onChange={(e) => setCfg((prev) => ({ ...prev, anchoring: { ...prev.anchoring, execution_mode: e.target.value as any } }))}
            disabled={!canUse}
          >
            <option value="platform">platform</option>
            <option value="tenant">tenant</option>
          </select>
          {!canUse && <div className="text-[11px] text-slate-500">Pick a project to edit/save this setting.</div>}
        </div>

        <div className="rounded border p-3 bg-white/60 space-y-2">
          <div className="text-sm font-medium flex items-center gap-2">
            <Rocket className="h-4 w-4" /> Deploy anchoring contract (MetaMask)
          </div>
          <div className="text-xs text-slate-600">
            Deploys a new <code>EvidenceAnchor</code> using the <code>EvidenceAnchorFactory</code>.
            {canUse ? (
              <> It will then save the deployed address into this project’s config.</>
            ) : (
              <> Select a project first if you want the UI to persist the deployed address into config.</>
            )}
          </div>

          <div className="grid gap-2">
            <div>
              <label className="text-xs text-slate-600">Factory address</label>
              <input
                className="w-full border rounded px-3 py-2 font-mono text-xs"
                value={factoryAddr}
                onChange={(e) => setFactoryAddr(e.target.value)}
                placeholder="0x... (EvidenceAnchorFactory)"
              />
              <div className="text-[11px] text-slate-500">
                Tip: set <code>NEXT_PUBLIC_ANCHOR_FACTORY_ADDR</code> in web-alt env to prefill.
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-600">Chain name</label>
                <input className="w-full border rounded px-3 py-2" value={chainName} onChange={(e) => setChainName(e.target.value)} placeholder="flare" />
              </div>
              <div>
                <label className="text-xs text-slate-600">RPC URL (optional override)</label>
                <input className="w-full border rounded px-3 py-2" value={rpcUrl} onChange={(e) => setRpcUrl(e.target.value)} placeholder="https://..." />
              </div>
            </div>

            <button
              className="inline-flex items-center justify-center bg-slate-900 text-white rounded px-3 py-2 text-sm disabled:opacity-60"
              onClick={deployWithMetaMask}
              disabled={deploying}
            >
              {deploying ? "Deploying…" : "Connect + Deploy"}
            </button>

            {!canUse && deployResult && (
              <div className="text-xs text-amber-700">
                Deployed successfully. Now register/select a project to save this anchor address into project config.
              </div>
            )}

            {deployResult && (
              <div className="rounded border p-3 bg-emerald-50 space-y-1">
                <div className="text-xs text-emerald-800 font-medium">Deployed</div>
                <div className="text-xs text-slate-700 break-all">factory: {deployResult.factory}</div>
                <div className="text-xs text-slate-700 break-all">anchor: {deployResult.anchor}</div>
                <div className="text-xs text-slate-700 break-all">tx: {deployResult.txHash}</div>
                {defaultExplorerBaseUrl ? (
                  <div className="text-xs text-slate-700 break-all">
                    explorer:{" "}
                    <a className="underline" href={`${defaultExplorerBaseUrl.replace(/\/$/, "")}/tx/${deployResult.txHash}`} target="_blank" rel="noreferrer">
                      view tx
                    </a>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="rounded border p-3 bg-white/60 space-y-2">
          <div className="text-sm font-medium">Current chains</div>
          {cfg.anchoring.chains.length ? (
            <div className="space-y-2">
              {cfg.anchoring.chains.map((c) => {
                const explorer = (c.explorer_base_url || (c.name.toLowerCase() === "flare" ? "https://flarescan.com" : ""))
                  .toString()
                  .replace(/\/$/, "");
                const contractUrl = explorer ? `${explorer}/address/${c.contract}` : null;
                return (
                  <div key={c.name} className="rounded border p-2 bg-white">
                    <div className="text-xs text-slate-600">{c.name}</div>
                    <div className="text-xs font-mono break-all">
                      {c.contract}
                      {contractUrl ? (
                        <>
                          {" "}
                          <a className="underline" href={contractUrl} target="_blank" rel="noreferrer">
                            (explorer)
                          </a>
                        </>
                      ) : null}
                    </div>
                    {c.rpc_url ? <div className="text-xs text-slate-600 break-all">rpc_url={c.rpc_url}</div> : null}
                    {c.explorer_base_url ? <div className="text-xs text-slate-600 break-all">explorer={c.explorer_base_url}</div> : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-sm text-slate-600">No chains configured.</div>
          )}
        </div>

        {error && <div className="text-sm text-red-600">Error: {error}</div>}
        {message && <div className="text-sm text-emerald-700">{message}</div>}
      </div>

      <div className="text-xs text-slate-500">
        Config is saved via <code>{"/api/proxy/v1/projects/<id>/config"}</code>, so API keys remain server-side.
      </div>
    </div>
  );
}
