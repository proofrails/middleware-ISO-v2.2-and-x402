"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Wand2, MessageSquare, Save, Rocket, Sparkles } from "lucide-react";
import { aiAssist, listReceipts, getAIStatus, type AIAssistRequest, type AIMessage, type ReceiptsPage } from "../lib/api";
import { useProjectStore } from "../lib/client/useProjectStore";

function uidClientOnly() {
  // Important: this must only run in the browser to avoid SSR hydration mismatches.
  if (typeof window !== "undefined" && typeof crypto !== "undefined" && "randomUUID" in crypto) return (crypto as any).randomUUID();
  return Math.random().toString(36).slice(2);
}

export default function AssistantPanel() {
  const { activeProject, loading: projectLoading } = useProjectStore();

  // NOTE: sessionId must not be generated during SSR (it causes hydration mismatch).
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    setSessionId((prev) => prev || `ui-${uidClientOnly()}`);
  }, []);

  const [history, setHistory] = useState<{ role: "user" | "assistant"; text: string }[]>([
    { role: "assistant", text: "Hi! I can help with SDK setup, receipt exploration, and verification. Try: 'List receipts' or 'SDK help (ts)'." },
  ]);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  // Safety toggles + scope
  const [allowReadReceipts, setAllowReadReceipts] = useState(false);
  const [allowReadArtifacts, setAllowReadArtifacts] = useState(false);
  const [allowConfigChanges, setAllowConfigChanges] = useState(false);
  const [allowedIds, setAllowedIds] = useState<string[]>([]);

  // Assist filters (optional)
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [chainFilter, setChainFilter] = useState<string>("");

  // AI Status
  const [aiStatus, setAiStatus] = useState<{ enabled: boolean; provider: string; model: string } | null>(null);
  useEffect(() => {
    getAIStatus()
      .then(setAiStatus)
      .catch(() => setAiStatus({ enabled: false, provider: "none", model: "(not configured)" }));
  }, []);

  // Receipt options for selection
  const [receipts, setReceipts] = useState<ReceiptsPage | null>(null);
  useEffect(() => {
    if (!allowReadReceipts) return;
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    if (chainFilter) params.chain = chainFilter;
    listReceipts({ page: 1, page_size: 50, ...params })
      .then(setReceipts)
      .catch(() => setReceipts(null));
  }, [allowReadReceipts, statusFilter, chainFilter]);

  const onToggleId = (id: string, checked: boolean) => {
    setAllowedIds((prev) => (checked ? Array.from(new Set([...prev, id])) : prev.filter((x) => x !== id)));
  };

  async function send() {
    const trimmed = msg.trim();
    if (!trimmed) return;

    // Ensure session exists.
    const sid = sessionId || `ui-${uidClientOnly()}`;
    if (!sessionId) setSessionId(sid);

    const local = [...history, { role: "user" as const, text: trimmed }];
    setHistory(local);
    setMsg("");
    setLoading(true);
    try {
      const messages: AIMessage[] = local.map(({ role, text }) => ({ role, content: text }));
      const scope = {
        allow_read_receipts: allowReadReceipts,
        allowed_receipt_ids: allowReadReceipts ? allowedIds : [],
        allow_read_artifacts: allowReadArtifacts,
        allow_config_changes: allowConfigChanges,
      };
      const req: AIAssistRequest = {
        messages,
        scope,
        session_id: sid,
        params: { filters: { status: statusFilter || undefined, chain: chainFilter || undefined } },
      };
      const res = await aiAssist(req);
      setHistory((h) => [...h, { role: "assistant", text: res.reply }]);
    } catch (e: any) {
      setHistory((h) => [...h, { role: "assistant", text: `Error: ${e?.message || e}` }]);
    } finally {
      setLoading(false);
    }
  }

  const logUrl = useMemo(() => {
    if (!sessionId) return null;
    const base = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
    return `${base.replace(/\/$/, "")}/files/ai_sessions/${sessionId}.log`;
  }, [sessionId]);

  return (
    <div className="shadow-sm ring-2 ring-slate-300 rounded-xl bg-white border border-slate-200">
      <div className="px-4 pt-4">
        <div className="text-base font-semibold flex items-center gap-2">
          <Wand2 className="h-4 w-4" /> AI Assistant
          {aiStatus && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${aiStatus.enabled ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}
              title={`Provider: ${aiStatus.provider}, Model: ${aiStatus.model}`}
            >
              {aiStatus.enabled ? (
                <>
                  <Sparkles className="h-3 w-3 inline mr-1" />
                  {aiStatus.provider}
                </>
              ) : (
                "Basic"
              )}
            </span>
          )}
        </div>
        <div className="text-xs text-slate-600">Chat • Results • Scoped access</div>
      </div>

      <div className="p-4 space-y-3">
        <div className="text-xs text-slate-600">
          Project: <span className="font-medium">{projectLoading ? "…" : activeProject ? activeProject.name : "(none)"}</span>
        </div>

        {/* Safety & Scope */}
        <div className="rounded-lg border p-3 bg-white/70 space-y-2">
          <div className="text-xs font-medium text-slate-600">Safety & Scope</div>
          <div className="space-y-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="accent-slate-900" checked={allowReadReceipts} onChange={(e) => setAllowReadReceipts(e.target.checked)} />
              Allow reading receipts
            </label>
            <div className="grid grid-cols-2 gap-2 pl-5">
              <div>
                <label className="text-xs text-slate-600">Status</label>
                <select className="w-full border rounded px-2 py-1" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} disabled={!allowReadReceipts}>
                  <option value="">(any)</option>
                  <option value="pending">pending</option>
                  <option value="anchored">anchored</option>
                  <option value="awaiting_anchor">awaiting_anchor</option>
                  <option value="failed">failed</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-600">Chain</label>
                <input className="w-full border rounded px-2 py-1" value={chainFilter} onChange={(e) => setChainFilter(e.target.value)} placeholder="flare" disabled={!allowReadReceipts} />
              </div>
            </div>
            {allowReadReceipts && (
              <div className="rounded border p-2 bg-white/60">
                <div className="text-xs text-slate-600 mb-1">Restrict to receipt IDs (optional)</div>
                <div className="max-h-32 overflow-auto space-y-1">
                  {receipts?.items?.length ? (
                    receipts.items.map((it) => (
                      <label key={it.id} className="flex items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          className="accent-slate-900"
                          checked={allowedIds.includes(it.id)}
                          onChange={(e) => onToggleId(it.id, e.target.checked)}
                        />
                        <span className="truncate" title={`${it.id} — ${it.status} ${it.amount} ${it.currency}`}>
                          {it.id} — {it.status}
                        </span>
                      </label>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500">No receipts loaded or not allowed.</div>
                  )}
                </div>
              </div>
            )}
            <label className="flex items-center gap-2">
              <input type="checkbox" className="accent-slate-900" checked={allowReadArtifacts} onChange={(e) => setAllowReadArtifacts(e.target.checked)} />
              Allow reading artifacts (vc.json)
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="accent-slate-900" checked={allowConfigChanges} onChange={(e) => setAllowConfigChanges(e.target.checked)} />
              Allow config changes (dangerous; off by default)
            </label>
          </div>
        </div>

        {/* Chat area */}
        <div className="rounded-lg border p-3 bg-white/70">
          <div className="h-40 overflow-auto space-y-2 text-sm">
            {history.map((h, i) => (
              <div key={i} className={`flex ${h.role === "assistant" ? "justify-start" : "justify-end"}`}>
                <div
                  className={`px-3 py-2 rounded-xl max-w-[85%] ${h.role === "assistant" ? "bg-slate-100 text-slate-900" : "bg-slate-900 text-white"}`}
                >
                  {h.text}
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              placeholder="Ask: List receipts, Receipt <id>, Verify <bundle_url>, SDK help (ts)…"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <button
              className="inline-flex items-center bg-slate-900 text-white rounded px-3 py-2 text-sm disabled:opacity-60"
              onClick={send}
              disabled={loading}
              title="Send"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              {loading ? "Sending…" : "Ask"}
            </button>
          </div>
        </div>

        {/* Results helpers */}
        <div className="rounded-lg border p-3 bg-white/70 space-y-2 text-sm">
          <div className="font-medium">Session</div>
          <div className="text-slate-700 text-xs break-all">Session ID: {sessionId || "(initializing…)"}</div>
          <div className="mt-2 flex gap-2">
            {logUrl ? (
              <a
                href={logUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                title="Download session log"
              >
                <Save className="h-4 w-4 mr-2" />
                Session Log
              </a>
            ) : (
              <span className="inline-flex items-center rounded border px-3 py-2 text-sm text-slate-400" title="Session ID not ready yet">
                <Save className="h-4 w-4 mr-2" />
                Session Log
              </span>
            )}
            <button
              className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
              onClick={() => setHistory([{ role: "assistant", text: "Cleared. Ask me anything about receipts, SDKs or verification." }])}
              title="Clear chat"
            >
              <Rocket className="h-4 w-4 mr-2" />
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
