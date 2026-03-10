"use client";

import React, { useEffect, useMemo, useState } from "react";
import { KeyRound, PlusCircle, Trash2, Copy, Link as LinkIcon } from "lucide-react";
import { useProjectStore } from "../lib/client/useProjectStore";
import ConnectionStringGenerator from "./ConnectionStringGenerator";

type APIKeyInfo = {
  id: string;
  label: string;
  role: string;
  project_id?: string | null;
  created_at: string;
  revoked_at?: string | null;
};

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}

export default function APIKeysPanel() {
  const { activeProject, loading: projectLoading } = useProjectStore();

  const [keys, setKeys] = useState<APIKeyInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [label, setLabel] = useState("dev-key");
  const [lastCreatedKey, setLastCreatedKey] = useState<string | null>(null);

  const canUse = useMemo(() => !projectLoading && !!activeProject, [projectLoading, activeProject]);

  async function refresh() {
    if (!canUse) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/proxy/v1/auth/api-keys", { cache: "no-store" });
      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        throw new Error(`list_api_keys_failed:${r.status}:${txt}`);
      }
      const data = (await r.json()) as APIKeyInfo[];
      setKeys(data);
    } catch (e: any) {
      setError(String(e?.message || e));
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }

  async function createKey() {
    if (!canUse) return;
    setCreating(true);
    setError(null);
    setLastCreatedKey(null);
    try {
      const r = await fetch("/api/proxy/v1/auth/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
      });
      const txt = await r.text().catch(() => "");
      if (!r.ok) {
        throw new Error(`create_api_key_failed:${r.status}:${txt}`);
      }
      // Backend returns the secret ONLY in X-API-Key header
      const secret = r.headers.get("X-API-Key");
      if (secret) setLastCreatedKey(secret);

      // refresh list
      await refresh();
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id: string) {
    if (!canUse) return;
    if (!confirm("Revoke this API key?")) return;
    setError(null);
    try {
      const r = await fetch(`/api/proxy/v1/auth/api-keys/${id}`, { method: "DELETE" });
      const txt = await r.text().catch(() => "");
      if (!r.ok) {
        throw new Error(`revoke_api_key_failed:${r.status}:${txt}`);
      }
      await refresh();
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => {
    refresh().catch(() => void 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canUse]);

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> API Keys
          </div>
          <div className="text-xs text-slate-600">Create / list / revoke keys for the active project</div>
        </div>
        <a className="text-xs text-slate-600 underline" href={`${apiBase()}/docs`} target="_blank" rel="noreferrer">
          backend
        </a>
      </div>

      {!canUse && <div className="text-sm text-slate-600">Select or register a project to manage API keys.</div>}

      {canUse && (
        <div className="rounded border p-3 bg-white/60 space-y-2">
          <div className="text-xs text-slate-600">Create a new API key (secret is returned once)</div>
          <div className="flex gap-2">
            <input className="flex-1 border rounded px-3 py-2" value={label} onChange={(e) => setLabel(e.target.value)} />
            <button
              className="inline-flex items-center justify-center bg-slate-900 text-white rounded px-3 py-2 text-sm disabled:opacity-60"
              onClick={createKey}
              disabled={creating}
              title="Create API key"
            >
              <PlusCircle className="h-4 w-4 mr-2" />
              {creating ? "Creating…" : "Create"}
            </button>
          </div>

          {lastCreatedKey && (
            <div className="space-y-3">
              <div className="rounded border p-3 bg-emerald-50">
                <div className="text-xs text-emerald-800 font-medium">New API key (copy now; it will not be shown again)</div>
                <div className="mt-2 flex gap-2">
                  <input className="flex-1 border rounded px-3 py-2 font-mono text-xs" value={lastCreatedKey} readOnly />
                  <button
                    className="rounded border px-3 py-2 text-sm hover:bg-white"
                    onClick={() => navigator.clipboard.writeText(lastCreatedKey).catch(() => void 0)}
                    title="Copy"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <ConnectionStringGenerator 
                apiKey={lastCreatedKey} 
                projectName={activeProject?.name}
              />
            </div>
          )}

          {error && <div className="text-sm text-red-600">Error: {error}</div>}

          <div className="mt-2 text-xs text-slate-600">Existing keys</div>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : keys.length ? (
            <div className="space-y-2">
              {keys
                .slice()
                .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
                .map((k) => {
                  const revoked = !!k.revoked_at;
                  return (
                    <div key={k.id} className="flex items-center justify-between gap-2 rounded border p-2 bg-white">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{k.label}</div>
                        <div className="text-xs text-slate-600 truncate">
                          role={k.role} • created={k.created_at}
                          {revoked ? ` • revoked=${k.revoked_at}` : ""}
                        </div>
                      </div>
                      <button
                        className="rounded border px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
                        onClick={() => revokeKey(k.id)}
                        disabled={revoked}
                        title={revoked ? "Already revoked" : "Revoke"}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
            </div>
          ) : (
            <div className="text-sm text-slate-600">No keys found for this project.</div>
          )}
        </div>
      )}

      <div className="text-xs text-slate-500">
        Keys are created by calling <code>/v1/auth/api-keys</code> through <code>/api/proxy</code> so the active project’s cookie-auth key is used.
        The raw key secret is returned only once in the <code>X-API-Key</code> response header.
      </div>
    </div>
  );
}
