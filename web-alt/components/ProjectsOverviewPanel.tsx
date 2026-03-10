"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Layers, RefreshCcw } from "lucide-react";

type ChainCfg = {
  name: string;
  contract: string;
  rpc_url?: string | null;
  explorer_base_url?: string | null;
};

type ProjectDetails = {
  id: string;
  name: string;
  owner_wallet: string;
  created_at: string;
  ok: boolean;
  error?: string;
  anchoring: null | { execution_mode?: string; chains?: ChainCfg[] };
};

type DetailsResponse = {
  active_project_id?: string;
  projects: ProjectDetails[];
};

export default function ProjectsOverviewPanel() {
  const [data, setData] = useState<DetailsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/store/projects/details", { cache: "no-store" });
      const txt = await r.text().catch(() => "");
      if (!r.ok) throw new Error(`details_fetch_failed:${r.status}:${txt}`);
      setData(JSON.parse(txt));
    } catch (e: any) {
      setError(String(e?.message || e));
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch(() => void 0);
  }, []);

  const projects = useMemo(() => data?.projects || [], [data?.projects]);

  const activeName = useMemo(() => {
    const active = projects.find((p) => p.id === data?.active_project_id);
    return active?.name || null;
  }, [projects, data?.active_project_id]);

  async function setActive(projectId: string) {
    await fetch("/api/store/projects/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    await load();
  }

  function modeBadge(mode: string | undefined) {
    const m = (mode || "platform").toLowerCase();
    const style =
      m === "tenant"
        ? "bg-amber-100 text-amber-800 border-amber-200"
        : "bg-slate-100 text-slate-700 border-slate-200";
    return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${style}`}>{m}</span>;
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold flex items-center gap-2">
            <Layers className="h-4 w-4" /> Projects overview
          </div>
          <div className="text-xs text-slate-600">See how each saved project is anchored (hosted vs self-hosted)</div>
        </div>
        <button
          className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
          onClick={load}
          disabled={loading}
          title="Refresh"
        >
          <RefreshCcw className="h-4 w-4 mr-2" /> {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {activeName && (
        <div className="text-xs text-slate-600">
          Active: <span className="font-medium">{activeName}</span>
        </div>
      )}

      {error && <div className="text-sm text-red-600">Error: {error}</div>}

      {projects.length ? (
        <div className="space-y-2">
          {projects.map((p) => {
            const isActive = p.id === data?.active_project_id;
            const mode = p.anchoring?.execution_mode || "platform";
            const chains = p.anchoring?.chains || [];
            return (
              <div key={p.id} className={`rounded border p-3 ${isActive ? "bg-slate-900 text-white" : "bg-white/60"}`}>
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold">{p.name}</div>
                    <div className={`text-xs break-all ${isActive ? "text-white/80" : "text-slate-600"}`}>{p.owner_wallet}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {modeBadge(mode)}
                    <button
                      className={`rounded border px-2 py-1 text-xs ${isActive ? "border-white/30 hover:bg-white/10" : "hover:bg-slate-50"}`}
                      onClick={() => setActive(p.id)}
                      title="Set active"
                    >
                      Set active
                    </button>
                  </div>
                </div>

                {!p.ok ? (
                  <div className={`mt-2 text-xs ${isActive ? "text-white/80" : "text-red-600"}`}>config: {p.error || "failed"}</div>
                ) : (
                  <div className="mt-2 space-y-1">
                    <div className={`text-xs ${isActive ? "text-white/80" : "text-slate-600"}`}>Chains: {chains.length || 0}</div>
                    {chains.slice(0, 3).map((c) => {
                      const explorer = (c.explorer_base_url || (c.name?.toLowerCase() === "flare" ? "https://flarescan.com" : ""))
                        .toString()
                        .replace(/\/$/, "");
                      const contractUrl = explorer ? `${explorer}/address/${c.contract}` : null;
                      return (
                        <div key={c.name + c.contract} className={`text-xs font-mono break-all ${isActive ? "text-white" : "text-slate-700"}`}>
                          {c.name}: {c.contract}
                          {contractUrl ? (
                            <a className="underline ml-1" href={contractUrl} target="_blank" rel="noreferrer">
                              (explorer)
                            </a>
                          ) : null}
                        </div>
                      );
                    })}
                    {chains.length > 3 ? (
                      <div className={`text-xs ${isActive ? "text-white/80" : "text-slate-600"}`}>…and {chains.length - 3} more</div>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-sm text-slate-600">No saved projects yet. Register a project first.</div>
      )}

      <div className="text-xs text-slate-500">
        This panel calls <code>/api/store/projects/details</code> so API keys remain server-side.
      </div>
    </div>
  );
}
