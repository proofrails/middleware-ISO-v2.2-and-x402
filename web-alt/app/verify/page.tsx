"use client";
import { useState } from "react";
import VerificationResultCard from "../../components/receipt/VerificationResultCard";
import { verifyEvidence, type VerificationResult } from "../../lib/proofrails";

export default function VerifyPage() {
  const [receiptId, setReceiptId] = useState("");
  const [bundleHash, setBundleHash] = useState("");
  const [bundleUrl, setBundleUrl] = useState("");
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [busy, setBusy] = useState(false);
  async function run() { setBusy(true); try { setResult(await verifyEvidence({ receipt_id: receiptId || undefined, bundle_hash: bundleHash || undefined, bundle_url: bundleUrl || undefined })); } finally { setBusy(false); } }
  const cls = "mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm outline-none focus:border-slate-950";
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-4xl font-black tracking-tight">Verify a receipt</h1>
        <p className="mt-2 text-slate-600">Check whether a receipt, bundle hash, or evidence URL matches its ProofRails record and onchain anchor.</p>
        <div className="mt-6 space-y-4">
          <label className="block text-sm font-semibold">Receipt ID<input className={cls} value={receiptId} onChange={(e)=>setReceiptId(e.target.value)} placeholder="receipt uuid or demo id" /></label>
          <label className="block text-sm font-semibold">Bundle hash<input className={cls} value={bundleHash} onChange={(e)=>setBundleHash(e.target.value)} placeholder="0x..." /></label>
          <label className="block text-sm font-semibold">Bundle URL<input className={cls} value={bundleUrl} onChange={(e)=>setBundleUrl(e.target.value)} placeholder="https://.../evidence.zip" /></label>
          <button onClick={run} disabled={busy} className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-bold text-white disabled:opacity-60">{busy ? "Verifying..." : "Verify"}</button>
        </div>
      </section>
      {result && <VerificationResultCard result={result} />}
    </div>
  );
}
