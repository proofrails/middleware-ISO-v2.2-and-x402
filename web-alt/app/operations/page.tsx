"use client";

import React, { useState } from "react";
import AssistantPanel from "../../components/AssistantPanel";
import { verifyBundle, verifyCid, camt053, camt052 } from "../../lib/api";

export default function OperationsPage() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  // Verify section state
  const [bundleUrl, setBundleUrl] = useState("");
  const [cid, setCid] = useState("");
  const [store, setStore] = useState<"auto" | "ipfs" | "arweave">("auto");
  const [receiptIdForCid, setReceiptIdForCid] = useState("");
  const [verifyResult, setVerifyResult] = useState<any>(null);

  // Statements state
  const [date053, setDate053] = useState("");
  const [date052, setDate052] = useState("");
  const [window052, setWindow052] = useState("00:00-23:59");
  const [stmtResult, setStmtResult] = useState<any>(null);

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left sidebar - Recent activity */}
      <aside className="col-span-12 lg:col-span-3 space-y-4">
        <div className="card p-4">
          <div className="text-base font-semibold mb-2">Recent Activity</div>
          <div className="text-sm text-slate-600">
            Your recent verifications and statement generations will appear here.
          </div>
        </div>

        <div className="card p-4">
          <div className="text-sm font-semibold mb-2">Quick Links</div>
          <div className="space-y-2 text-sm">
            <a href={`${apiBase}/docs#/verify`} target="_blank" rel="noreferrer" className="block text-slate-600 hover:text-slate-900 underline">
              Verification API Docs
            </a>
            <a href={`${apiBase}/docs#/statements`} target="_blank" rel="noreferrer" className="block text-slate-600 hover:text-slate-900 underline">
              Statements API Docs
            </a>
          </div>
        </div>
      </aside>

      {/* Center content */}
      <section className="col-span-12 lg:col-span-6 space-y-4">
        <div className="card p-4">
          <div className="text-lg font-bold mb-1">Operations</div>
          <div className="text-sm text-slate-600">Verification and statement generation tools</div>
        </div>

        {/* Verification Section */}
        <div className="card p-4">
          <div className="text-base font-semibold mb-3">Bundle Verification</div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-slate-600 mb-1">Verify by Bundle URL</div>
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded px-3 py-2"
                  value={bundleUrl}
                  onChange={(e) => setBundleUrl(e.target.value)}
                  placeholder={`${apiBase}/files/<rid>/evidence.zip`}
                />
                <button
                  className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                  onClick={async () => {
                    try {
                      const res = await verifyBundle({ bundle_url: bundleUrl || undefined });
                      setVerifyResult(res);
                    } catch (e: any) {
                      setVerifyResult({ error: String(e?.message || e) });
                    }
                  }}
                >
                  Verify
                </button>
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600 mb-1">Verify by CID (IPFS/Arweave)</div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="border rounded px-3 py-2 col-span-2"
                  value={cid}
                  onChange={(e) => setCid(e.target.value)}
                  placeholder="Qm... / bafy... / arweave-txid"
                />
                <select
                  className="border rounded px-2 py-2"
                  value={store}
                  onChange={(e) => setStore(e.target.value as any)}
                >
                  <option value="auto">auto</option>
                  <option value="ipfs">ipfs</option>
                  <option value="arweave">arweave</option>
                </select>
                <input
                  className="border rounded px-3 py-2"
                  value={receiptIdForCid}
                  onChange={(e) => setReceiptIdForCid(e.target.value)}
                  placeholder="receipt_id (optional)"
                />
                <button
                  className="col-span-2 inline-flex items-center justify-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                  onClick={async () => {
                    try {
                      const res = await verifyCid({
                        cid,
                        store,
                        receipt_id: receiptIdForCid || undefined,
                      });
                      setVerifyResult(res);
                    } catch (e: any) {
                      setVerifyResult({ error: String(e?.message || e) });
                    }
                  }}
                >
                  Verify CID
                </button>
              </div>
            </div>
          </div>
          {verifyResult && (
            <div className="mt-3 rounded border p-3 bg-white/60">
              <div className="text-xs text-slate-600 mb-1">Verification Result</div>
              <pre className="text-xs bg-slate-950 text-slate-100 p-3 rounded-lg overflow-auto max-h-64">
{JSON.stringify(verifyResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Statements Section */}
        <div className="card p-4">
          <div className="text-base font-semibold mb-3">Statement Generation</div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-slate-600 mb-1">camt.053 (Daily Statement)</div>
              <div className="flex gap-2">
                <input 
                  type="date" 
                  className="flex-1 border rounded px-3 py-2" 
                  value={date053} 
                  onChange={(e) => setDate053(e.target.value)} 
                />
                <button
                  className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                  onClick={async () => {
                    if (!date053) return;
                    try {
                      const res = await camt053(date053);
                      setStmtResult(res);
                    } catch (e: any) {
                      setStmtResult({ error: String(e?.message || e) });
                    }
                  }}
                >
                  Generate
                </button>
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600 mb-1">camt.052 (Intraday Statement)</div>
              <div className="grid grid-cols-2 gap-2">
                <input 
                  type="date" 
                  className="border rounded px-3 py-2" 
                  value={date052} 
                  onChange={(e) => setDate052(e.target.value)} 
                />
                <input 
                  className="border rounded px-3 py-2" 
                  value={window052} 
                  onChange={(e) => setWindow052(e.target.value)} 
                  placeholder="HH:MM-HH:MM" 
                />
                <button
                  className="col-span-2 inline-flex items-center justify-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                  onClick={async () => {
                    if (!date052 || !window052) return;
                    try {
                      const res = await camt052(date052, window052);
                      setStmtResult(res);
                    } catch (e: any) {
                      setStmtResult({ error: String(e?.message || e) });
                    }
                  }}
                >
                  Generate
                </button>
              </div>
            </div>
          </div>
          {stmtResult && (
            <div className="mt-3 rounded border p-3 bg-white/60">
              <div className="text-xs text-slate-600 mb-1">Statement Result</div>
              <pre className="text-xs bg-slate-950 text-slate-100 p-3 rounded-lg overflow-auto max-h-64">
{JSON.stringify(stmtResult, null, 2)}
              </pre>
              {stmtResult.url && (
                <div className="mt-2">
                  <a 
                    className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50" 
                    href={`${apiBase}${stmtResult.url}`} 
                    target="_blank" 
                    rel="noreferrer"
                  >
                    Download Statement
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card p-4 bg-slate-50">
          <div className="text-sm font-medium mb-2">About This Page</div>
          <div className="text-sm text-slate-600 space-y-1">
            <p>• <strong>Verification</strong>: Validate evidence bundles by URL, hash, or CID (IPFS/Arweave)</p>
            <p>• <strong>Statements</strong>: Generate ISO 20022 banking statements (camt.052/053)</p>
            <p>• <strong>AI Assistant</strong>: Get help with verification and statement generation</p>
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
