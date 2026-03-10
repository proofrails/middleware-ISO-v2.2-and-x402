"use client";

export const dynamic = "force-dynamic";

import React, { useEffect, useMemo, useState } from "react";
import { Wallet } from "lucide-react";
import { BrowserProvider, Contract } from "ethers";
import Link from "next/link";
import AssistantPanel from "../components/AssistantPanel";
import ProjectsOverviewPanel from "../components/ProjectsOverviewPanel";
import { listReceipts, type ReceiptsPage, refund } from "../lib/api";

function StatusBadge({ status }: { status: string }) {
  const style =
    status === "awaiting_anchor"
      ? "bg-amber-100 text-amber-800 border-amber-200"
      : status === "anchored"
        ? "bg-emerald-100 text-emerald-800 border-emerald-200"
        : status === "failed"
          ? "bg-red-100 text-red-800 border-red-200"
          : "bg-slate-100 text-slate-700 border-slate-200";

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${style}`}>{status}</span>
  );
}

type ProjectAnchoringChain = {
  name: string;
  contract: string;
  rpc_url?: string | null;
  explorer_base_url?: string | null;
};

type ProjectConfig = {
  anchoring: { execution_mode: "platform" | "tenant"; chains: ProjectAnchoringChain[] };
};

const ANCHOR_ABI = [
  {
    type: "event",
    name: "EvidenceAnchored",
    inputs: [
      { indexed: false, name: "bundleHash", type: "bytes32" },
      { indexed: true, name: "sender", type: "address" },
      { indexed: false, name: "ts", type: "uint256" },
    ],
  },
  {
    type: "function",
    name: "anchorEvidence",
    stateMutability: "nonpayable",
    inputs: [{ name: "bundleHash", type: "bytes32" }],
    outputs: [],
  },
] as const;

export default function Page() {
  const [receipts, setReceipts] = useState<ReceiptsPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<"mine" | "all">("mine");

  // Modal states
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmReceiptId, setConfirmReceiptId] = useState<string>("");
  const [confirmChain, setConfirmChain] = useState<string>("");
  const [confirmTxid, setConfirmTxid] = useState<string>("");
  const [confirmErr, setConfirmErr] = useState<string | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  const [anchorOpen, setAnchorOpen] = useState(false);
  const [anchorReceiptId, setAnchorReceiptId] = useState<string>("");
  const [anchorBusy, setAnchorBusy] = useState(false);
  const [anchorErr, setAnchorErr] = useState<string | null>(null);
  const [anchorCfg, setAnchorCfg] = useState<ProjectConfig | null>(null);
  const [anchorChainName, setAnchorChainName] = useState<string>("");
  const [anchorBundleHash, setAnchorBundleHash] = useState<string>("");

  const [refundOpen, setRefundOpen] = useState(false);
  const [refundReceiptId, setRefundReceiptId] = useState<string>("");
  const [refundReasonCode, setRefundReasonCode] = useState<string>("CUST");
  const [refundBusy, setRefundBusy] = useState(false);
  const [refundErr, setRefundErr] = useState<string | null>(null);

  const receiptById = useMemo(() => {
    const m = new Map<string, any>();
    receipts?.items?.forEach((r: any) => m.set(r.id, r));
    return m;
  }, [receipts]);

  async function loadReceipts(nextScope: "mine" | "all" = scope) {
    setLoading(true);
    try {
      const r = await listReceipts({ page: 1, page_size: 10, scope: nextScope });
      setReceipts(r);
      setError(null);
      setScope(nextScope);
    } catch (e: any) {
      const msg = String(e?.message || e);
      if (nextScope === "all" && msg.includes("403")) {
        setError("scope=all requires an admin key; falling back to scope=mine.");
        const r = await listReceipts({ page: 1, page_size: 10, scope: "mine" });
        setReceipts(r);
        setScope("mine");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReceipts("mine").catch((e) => setError(String(e?.message || e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openConfirmAnchor(it: any) {
    setConfirmReceiptId(it.id);
    setConfirmChain(it.chain || "");
    setConfirmTxid("");
    setConfirmErr(null);
    setConfirmOpen(true);
  }

  function openRefund(it: any) {
    setRefundReceiptId(it.id);
    setRefundReasonCode("CUST");
    setRefundErr(null);
    setRefundOpen(true);
  }

  async function submitRefund() {
    setRefundBusy(true);
    setRefundErr(null);
    try {
      await refund({
        original_receipt_id: refundReceiptId,
        reason_code: refundReasonCode || undefined,
      });
      setRefundOpen(false);
      await loadReceipts(scope);
    } catch (e: any) {
      setRefundErr(String(e?.message || e));
    } finally {
      setRefundBusy(false);
    }
  }

  async function submitConfirmAnchor() {
    setConfirmBusy(true);
    setConfirmErr(null);
    try {
      const r = await fetch("/api/proxy/v1/iso/confirm-anchor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          receipt_id: confirmReceiptId,
          chain: confirmChain || undefined,
          flare_txid: confirmTxid,
        }),
      });

      const txt = await r.text().catch(() => "");
      if (!r.ok) {
        if (r.status === 409) {
          throw new Error("invalid_status_transition (receipt must be awaiting_anchor or pending)");
        }
        if (r.status === 403) {
          throw new Error("forbidden (must be same project or admin)");
        }
        throw new Error(`${r.status} ${txt}`);
      }

      setConfirmOpen(false);
      await loadReceipts(scope);
    } catch (e: any) {
      setConfirmErr(String(e?.message || e));
    } finally {
      setConfirmBusy(false);
    }
  }

  async function openAnchorNow(it: any) {
    setAnchorReceiptId(it.id);
    setAnchorErr(null);
    setAnchorBusy(false);
    setAnchorCfg(null);
    setAnchorChainName("");
    setAnchorBundleHash("");
    setAnchorOpen(true);

    try {
      const storeRes = await fetch("/api/store/projects", { cache: "no-store" });
      const storeTxt = await storeRes.text().catch(() => "");
      if (!storeRes.ok) throw new Error(`store_fetch_failed:${storeRes.status}:${storeTxt}`);
      const storeObj = JSON.parse(storeTxt) as any;
      const projId = storeObj?.active_project_id;
      if (!projId) throw new Error("no_active_project");

      const cfgRes = await fetch(`/api/proxy/v1/projects/${projId}/config`, { cache: "no-store" });
      const cfgTxt = await cfgRes.text().catch(() => "");
      if (!cfgRes.ok) throw new Error(`load_project_config_failed:${cfgRes.status}:${cfgTxt}`);
      const cfgObj = JSON.parse(cfgTxt) as ProjectConfig;
      setAnchorCfg(cfgObj);

      const recRes = await fetch(`/api/proxy/v1/iso/receipts/${it.id}`, { cache: "no-store" });
      const recTxt = await recRes.text().catch(() => "");
      if (!recRes.ok) throw new Error(`load_receipt_failed:${recRes.status}:${recTxt}`);
      const recObj = JSON.parse(recTxt) as any;
      const bh = String(recObj.bundle_hash || "");
      if (!bh.startsWith("0x") || bh.length !== 66) throw new Error("receipt_missing_bundle_hash");
      setAnchorBundleHash(bh);

      const chains = cfgObj?.anchoring?.chains || [];
      if (!chains.length) throw new Error("project_missing_chains");
      setAnchorChainName(chains[0].name);
    } catch (e: any) {
      setAnchorErr(String(e?.message || e));
    }
  }

  async function submitAnchorNow() {
    setAnchorBusy(true);
    setAnchorErr(null);

    try {
      const { detectEthereumProvider } = await import("../lib/client/ethereum");
      const eth = await detectEthereumProvider({ timeoutMs: 2500, preferMetaMask: true });
      if (!eth)
        throw new Error(
          "No wallet found (EIP-1193 provider missing). Make sure MetaMask is installed/enabled for this site. " +
            "If you're using Brave, check Settings → Wallet → Default wallet (MetaMask) and reload."
        );
      if (!anchorCfg) throw new Error("missing_project_config");
      if (!anchorBundleHash) throw new Error("missing_bundle_hash");

      const chains = anchorCfg.anchoring?.chains || [];
      const chain = chains.find((c) => c.name === anchorChainName) || null;
      if (!chain) throw new Error("unknown_chain");
      if (!chain.contract) throw new Error("missing_chain_contract");

      try {
        await eth.request?.({ method: "eth_requestAccounts" });
      } catch {
        // ignore
      }
      const provider = new BrowserProvider(eth);
      const signer = await provider.getSigner();

      const contract = new Contract(chain.contract, ANCHOR_ABI as any, signer);
      const tx = await contract.anchorEvidence(anchorBundleHash);
      await tx.wait();

      const r = await fetch("/api/proxy/v1/iso/confirm-anchor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          receipt_id: anchorReceiptId,
          chain: chain.name,
          flare_txid: tx.hash,
        }),
      });
      const txt = await r.text().catch(() => "");
      if (!r.ok) throw new Error(`confirm_anchor_failed:${r.status}:${txt}`);

      setAnchorOpen(false);
      await loadReceipts(scope);
    } catch (e: any) {
      setAnchorErr(String(e?.message || e));
    } finally {
      setAnchorBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left sidebar */}
      <aside className="col-span-12 lg:col-span-3 space-y-4">
        <ProjectsOverviewPanel />
        
        <div className="card p-4">
          <div className="text-base font-semibold mb-2">Quick Actions</div>
          <div className="space-y-2">
            <Link href="/operations" className="block w-full text-left rounded border px-3 py-2 text-sm hover:bg-slate-50">
              → Verification & Statements
            </Link>
            <Link href="/settings" className="block w-full text-left rounded border px-3 py-2 text-sm hover:bg-slate-50">
              → Settings & Tools
            </Link>
          </div>
        </div>
      </aside>

      {/* Center content */}
      <section className="col-span-12 lg:col-span-6 space-y-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold">Receipts & Data</div>
              <div className="text-sm text-slate-600">Dashboard and receipt management</div>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <label className="flex items-center gap-2">
                <span>Scope</span>
                <select
                  className="border rounded px-2 py-1"
                  value={scope}
                  onChange={(e) => loadReceipts(e.target.value as any)}
                >
                  <option value="mine">mine</option>
                  <option value="all">all</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        {/* Refund modal */}
        {refundOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white border shadow-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base font-semibold">Initiate Refund</div>
                  <div className="text-xs text-slate-600 break-all">Receipt: {refundReceiptId}</div>
                </div>
                <button className="rounded border px-2 py-1 text-sm hover:bg-slate-50" onClick={() => setRefundOpen(false)}>
                  Close
                </button>
              </div>

              <div className="rounded border p-3 bg-white/60 space-y-2">
                <div className="text-xs text-slate-600">
                  This will create a new receipt with a pacs.004 payment return message.
                </div>
                <div>
                  <label className="text-xs text-slate-600">Reason Code (optional)</label>
                  <select
                    className="w-full border rounded px-3 py-2"
                    value={refundReasonCode}
                    onChange={(e) => setRefundReasonCode(e.target.value)}
                  >
                    <option value="CUST">CUST - Requested by Customer</option>
                    <option value="DUPL">DUPL - Duplicate Payment</option>
                    <option value="TECH">TECH - Technical Problem</option>
                    <option value="FRAD">FRAD - Fraudulent Transaction</option>
                    <option value="">None</option>
                  </select>
                </div>
              </div>

              {refundErr && <div className="text-sm text-red-600">Error: {refundErr}</div>}

              <div className="flex justify-end gap-2">
                <button className="rounded border px-3 py-2 text-sm hover:bg-slate-50" onClick={() => setRefundOpen(false)}>
                  Cancel
                </button>
                <button
                  className="rounded bg-slate-900 text-white px-3 py-2 text-sm disabled:opacity-60"
                  onClick={submitRefund}
                  disabled={refundBusy || !refundReceiptId}
                >
                  {refundBusy ? "Processing…" : "Initiate Refund"}
                </button>
              </div>

              <div className="text-xs text-slate-500">
                This will create a negative-amount receipt and generate pacs.004 XML for the return.
              </div>
            </div>
          </div>
        )}

        {/* Anchor-now modal */}
        {anchorOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white border shadow-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base font-semibold flex items-center gap-2">
                    <Wallet className="h-4 w-4" /> Anchor now (MetaMask)
                  </div>
                  <div className="text-xs text-slate-600 break-all">Receipt: {anchorReceiptId}</div>
                </div>
                <button className="rounded border px-2 py-1 text-sm hover:bg-slate-50" onClick={() => setAnchorOpen(false)}>
                  Close
                </button>
              </div>

              {anchorCfg && (
                <div className="rounded border p-3 bg-white/60 space-y-2">
                  <div className="text-xs text-slate-600">bundle_hash</div>
                  <div className="text-xs font-mono break-all">{anchorBundleHash || "(loading...)"}</div>

                  <div>
                    <label className="text-xs text-slate-600">Chain</label>
                    <select
                      className="w-full border rounded px-3 py-2"
                      value={anchorChainName}
                      onChange={(e) => setAnchorChainName(e.target.value)}
                    >
                      {(anchorCfg.anchoring?.chains || []).map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {anchorErr && <div className="text-sm text-red-600">Error: {anchorErr}</div>}

              <div className="flex justify-end gap-2">
                <button className="rounded border px-3 py-2 text-sm hover:bg-slate-50" onClick={() => setAnchorOpen(false)}>
                  Cancel
                </button>
                <button
                  className="rounded bg-slate-900 text-white px-3 py-2 text-sm disabled:opacity-60"
                  onClick={submitAnchorNow}
                  disabled={anchorBusy || !anchorCfg || !anchorBundleHash || !anchorChainName}
                >
                  {anchorBusy ? "Anchoring…" : "Anchor now"}
                </button>
              </div>

              <div className="text-xs text-slate-500">
                This will call <code>EvidenceAnchor.anchorEvidence(bundle_hash)</code> from your wallet, then auto-submit
                to <code>/v1/iso/confirm-anchor</code>.
              </div>
            </div>
          </div>
        )}

        {/* Confirm-anchor modal */}
        {confirmOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white border shadow-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base font-semibold">Confirm anchor (manual)</div>
                  <div className="text-xs text-slate-600 break-all">Receipt: {confirmReceiptId}</div>
                  <div className="text-xs text-slate-600">Status: {String(receiptById.get(confirmReceiptId)?.status || "")}</div>
                </div>
                <button className="rounded border px-2 py-1 text-sm hover:bg-slate-50" onClick={() => setConfirmOpen(false)}>
                  Close
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="col-span-2">
                  <label className="text-xs text-slate-600">Chain name</label>
                  <input className="w-full border rounded px-3 py-2" value={confirmChain} onChange={(e) => setConfirmChain(e.target.value)} placeholder="flare" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-slate-600">Txid</label>
                  <input className="w-full border rounded px-3 py-2 font-mono text-xs" value={confirmTxid} onChange={(e) => setConfirmTxid(e.target.value)} placeholder="0x..." />
                </div>
              </div>

              {confirmErr && <div className="text-sm text-red-600">Error: {confirmErr}</div>}

              <div className="flex justify-end gap-2">
                <button className="rounded border px-3 py-2 text-sm hover:bg-slate-50" onClick={() => setConfirmOpen(false)}>
                  Cancel
                </button>
                <button
                  className="rounded bg-slate-900 text-white px-3 py-2 text-sm disabled:opacity-60"
                  onClick={submitConfirmAnchor}
                  disabled={!confirmReceiptId || !confirmTxid || confirmBusy}
                >
                  {confirmBusy ? "Submitting…" : "Submit"}
                </button>
              </div>

              <div className="text-xs text-slate-500">
                This posts to <code>/v1/iso/confirm-anchor</code>.
              </div>
            </div>
          </div>
        )}

        {/* Receipts Table */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-base font-semibold">Recent Receipts</div>
            <div className="text-xs text-slate-600">scope: <code>{scope}</code></div>
          </div>
          {loading && <div className="text-sm text-slate-600">Loading…</div>}
          {error && <div className="text-sm text-red-600">Error: {error}</div>}
          {!loading && !error && (
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-600">
                  <tr>
                    <th className="py-2 pr-3">ID</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Amount</th>
                    <th className="py-2 pr-3">Currency</th>
                    <th className="py-2 pr-3">Chain</th>
                    <th className="py-2 pr-3">Reference</th>
                    <th className="py-2 pr-3">Created</th>
                    <th className="py-2 pr-3">Anchored</th>
                    <th className="py-2 pr-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {receipts?.items?.length ? (
                    receipts.items.map((it) => (
                      <tr key={it.id} className="border-t hover:bg-slate-50">
                        <td className="py-2 pr-3 whitespace-nowrap font-mono text-xs">{it.id.substring(0, 8)}...</td>
                        <td className="py-2 pr-3">
                          <StatusBadge status={it.status} />
                        </td>
                        <td className="py-2 pr-3">{it.amount}</td>
                        <td className="py-2 pr-3">{it.currency}</td>
                        <td className="py-2 pr-3">{it.chain}</td>
                        <td className="py-2 pr-3">{it.reference}</td>
                        <td className="py-2 pr-3 text-xs">{new Date(it.created_at).toLocaleDateString()}</td>
                        <td className="py-2 pr-3 text-xs">{it.anchored_at ? new Date(it.anchored_at).toLocaleDateString() : "-"}</td>
                        <td className="py-2 pr-3">
                          {it.status === "awaiting_anchor" ? (
                            <div className="flex gap-1">
                              <button
                                className="rounded border px-2 py-1 text-xs hover:bg-slate-50"
                                onClick={() => openAnchorNow(it)}
                              >
                                Anchor
                              </button>
                              <button
                                className="rounded border px-2 py-1 text-xs hover:bg-slate-50"
                                onClick={() => openConfirmAnchor(it)}
                              >
                                Confirm
                              </button>
                            </div>
                          ) : it.status === "anchored" ? (
                            <button
                              className="rounded border px-2 py-1 text-xs hover:bg-slate-50"
                              onClick={() => openRefund(it)}
                            >
                              Refund
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="py-3 text-slate-500 text-center" colSpan={9}>
                        No receipts found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card p-4 bg-slate-50">
          <div className="text-sm font-medium mb-2">About This Page</div>
          <div className="text-sm text-slate-600 space-y-1">
            <p>• <strong>Dashboard</strong>: Overview of recent receipts and quick statistics</p>
            <p>• <strong>Receipts Table</strong>: List with actions (refund, anchor, confirm)</p>
            <p>• <strong>AI Assistant</strong>: Context-aware help for receipt management</p>
            <p>• <strong>Quick Actions</strong>: Navigate to other pages for verification, statements, and settings</p>
          </div>
        </div>
      </section>

      {/* Right sidebar - AI Assistant */}
      <aside className="col-span-12 lg:col-span-3">
        <AssistantPanel />
      </aside>
    </div>
  );
}
