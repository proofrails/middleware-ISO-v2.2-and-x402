"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Wallet, PlusCircle, Trash2, LogOut, CheckCircle2 } from "lucide-react";
import { BrowserProvider } from "ethers";
import { detectEthereumProvider } from "../lib/client/ethereum";

type StorePublic = {
  active_project_id?: string;
  projects: Array<{ id: string; name: string; owner_wallet: string; created_at: string }>;
};

type NonceResponse = { nonce: string; domain: string };

type RegisterResponse = {
  project: { id: string; name: string; owner_wallet: string; created_at: string };
  api_key: string;
};

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}

function buildSiweMessage(args: { domain: string; address: string; nonce: string; chainId: number; uri: string }): string {
  // Minimal EIP-4361 format (the backend parser is simple and expects these fields).
  // Keep this stable to match app/auth/siwe.py parsing.
  return (
    `${args.domain} wants you to sign in with your Ethereum account:\n` +
    `${args.address}\n\n` +
    `URI: ${args.uri}\n` +
    `Version: 1\n` +
    `Chain ID: ${args.chainId}\n` +
    `Nonce: ${args.nonce}\n` +
    `Issued At: ${new Date().toISOString()}\n`
  );
}

export default function ProjectsPanel() {
  const [store, setStore] = useState<StorePublic>({ projects: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projectName, setProjectName] = useState("My Project");
  const [lastKey, setLastKey] = useState<string | null>(null);

  const active = useMemo(() => {
    if (store.active_project_id) {
      return store.projects.find((p) => p.id === store.active_project_id) || null;
    }
    return store.projects[0] || null;
  }, [store]);

  async function refresh() {
    const r = await fetch("/api/store/projects", { cache: "no-store" });
    const data = (await r.json()) as StorePublic;
    setStore(data);
  }

  useEffect(() => {
    refresh().catch(() => void 0);
  }, []);

  async function connectAndRegister() {
    setLoading(true);
    setError(null);
    setLastKey(null);
    try {
      const eth = await detectEthereumProvider({ timeoutMs: 2500, preferMetaMask: true });
      if (!eth) {
        const dbg =
          typeof window !== "undefined"
            ? `window.ethereum=${String(!!(window as any).ethereum)} providers=${String(
                Array.isArray((window as any).ethereum?.providers) ? (window as any).ethereum.providers.length : 0
              )}`
            : "no_window";

        throw new Error(
          `No wallet found (EIP-1193 provider missing). Make sure MetaMask is installed/enabled for this site. ` +
            `If you're using Brave, check Settings → Wallet → Default wallet (MetaMask) and reload. (${dbg})`
        );
      }

      // Prompt connect explicitly
      try {
        await eth.request?.({ method: "eth_requestAccounts" });
      } catch {
        // ignore; BrowserProvider.getSigner() will surface errors if needed
      }

      const provider = new BrowserProvider(eth);
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      const net = await provider.getNetwork();

      // 1) get nonce from backend (through proxy, so it uses correct host/origin)
      const nonceRes = await fetch("/api/proxy/v1/auth/nonce", { cache: "no-store" });
      if (!nonceRes.ok) {
        throw new Error(`nonce_failed: ${nonceRes.status} ${await nonceRes.text().catch(() => "")}`);
      }
      const nonceData = (await nonceRes.json()) as NonceResponse;

      // 2) build message
      const uri = window.location.origin;
      const msg = buildSiweMessage({
        domain: nonceData.domain,
        address,
        nonce: nonceData.nonce,
        chainId: Number(net.chainId),
        uri,
      });

      // 3) sign
      const signature = await signer.signMessage(msg);

      // 4) register project via store route (stores api key in httpOnly cookie)
      const reg = await fetch("/api/store/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: projectName, message: msg, signature }),
      });

      const txt = await reg.text();
      if (!reg.ok) {
        throw new Error(`register_failed: ${reg.status} ${txt}`);
      }
      const out = JSON.parse(txt) as RegisterResponse;
      setLastKey(out.api_key);

      await refresh();
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function setActive(projectId: string) {
    await fetch("/api/store/projects/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    await refresh();
  }

  async function remove(projectId: string) {
    await fetch(`/api/store/projects/${projectId}`, { method: "DELETE" });
    await refresh();
  }

  async function logout() {
    await fetch("/api/store/logout", { method: "POST" });
    await refresh();
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold">Projects</div>
          <div className="text-xs text-slate-600">SIWE registration + project switcher</div>
        </div>
        <a className="text-xs text-slate-600 underline" href={`${apiBase()}/docs`} target="_blank" rel="noreferrer">
          backend
        </a>
      </div>

      {active ? (
        <div className="rounded border p-3 bg-white/60">
          <div className="text-xs text-slate-600">Active</div>
          <div className="text-sm font-medium break-all">{active.name}</div>
          <div className="text-xs text-slate-600 break-all">{active.owner_wallet}</div>
        </div>
      ) : (
        <div className="text-sm text-slate-600">No active project yet.</div>
      )}

      <div className="grid gap-2">
        <input
          className="border rounded px-3 py-2"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Project name"
        />
        <button
          className="inline-flex items-center justify-center bg-slate-900 text-white rounded px-3 py-2 text-sm disabled:opacity-60"
          onClick={connectAndRegister}
          disabled={loading}
          title="Connect wallet and register project"
        >
          <Wallet className="h-4 w-4 mr-2" />
          {loading ? "Working…" : "Connect + Register"}
        </button>
      </div>

      {lastKey && (
        <div className="rounded border p-3 bg-emerald-50">
          <div className="text-xs text-emerald-800 font-medium flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> API key returned (copy now; stored server-side)
          </div>
          <div className="mt-2 flex gap-2">
            <input className="flex-1 border rounded px-3 py-2 font-mono text-xs" value={lastKey} readOnly />
            <button
              className="rounded border px-3 py-2 text-sm hover:bg-white"
              onClick={() => navigator.clipboard.writeText(lastKey).catch(() => void 0)}
              title="Copy"
            >
              Copy
            </button>
          </div>
        </div>
      )}

      {error && <div className="text-sm text-red-600">Error: {error}</div>}

      {store.projects.length > 0 && (
        <div className="rounded border p-3 bg-white/60">
          <div className="text-xs text-slate-600 mb-2">Saved projects</div>
          <div className="space-y-2">
            {store.projects.map((p) => {
              const isActive = p.id === store.active_project_id;
              return (
                <div key={p.id} className="flex items-center justify-between gap-2">
                  <button
                    className={`text-left flex-1 rounded px-2 py-2 border ${isActive ? "bg-slate-900 text-white" : "bg-white hover:bg-slate-50"}`}
                    onClick={() => setActive(p.id)}
                    title="Set active"
                  >
                    <div className="text-sm font-medium truncate">{p.name}</div>
                    <div className={`text-xs truncate ${isActive ? "text-white/80" : "text-slate-600"}`}>{p.owner_wallet}</div>
                  </button>
                  <button
                    className="rounded border px-3 py-2 text-sm hover:bg-slate-50"
                    onClick={() => remove(p.id)}
                    title="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>

          <div className="mt-3">
            <button className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" /> Logout (clear keys)
            </button>
          </div>
        </div>
      )}

      <div className="text-xs text-slate-500">All backend calls go through <code>/api/proxy</code> so API keys never hit the browser JS.</div>
    </div>
  );
}
