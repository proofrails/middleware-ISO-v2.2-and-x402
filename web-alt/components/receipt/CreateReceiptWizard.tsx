"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createReceipt, type CreateReceiptInput } from "../../lib/proofrails";

const initial: CreateReceiptInput = {
  chain: "flare",
  tip_tx_hash: "0xabc123def4567890abc123def4567890abc123def4567890abc123def4567890",
  amount: "100.00",
  currency: "FLR",
  sender_wallet: "0xSender000000000000000000000000000000000000",
  receiver_wallet: "0xReceiver0000000000000000000000000000000000",
  reference: "invoice-2026-001",
  metadata: { customer: "demo-customer" },
  tags: ["demo", "invoice"],
};

export default function CreateReceiptWizard() {
  const router = useRouter();
  const [form, setForm] = useState<CreateReceiptInput>(initial);
  const [metadataText, setMetadataText] = useState(JSON.stringify(initial.metadata, null, 2));
  const [tagsText, setTagsText] = useState(initial.tags?.join(", ") || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof CreateReceiptInput>(key: K, value: CreateReceiptInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      let metadata: Record<string, unknown> | undefined;
      if (metadataText.trim()) metadata = JSON.parse(metadataText);
      const tags = tagsText.split(",").map((t) => t.trim()).filter(Boolean);
      const out = await createReceipt({ ...form, metadata, tags });
      router.push(`/receipts/${out.receipt.id}?source=${out.source}`);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  const inputClass = "mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm outline-none focus:border-slate-900";
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <div className="text-sm font-bold uppercase tracking-wide text-slate-500">Create receipt</div>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950">Turn a transaction into evidence</h1>
        <p className="mt-2 text-slate-600">Enter the payment reference and context. ProofRails creates the receipt, ISO-style artifacts, evidence bundle, and verification link.</p>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <label className="text-sm font-semibold">Chain<input className={inputClass} value={form.chain} onChange={(e) => update("chain", e.target.value)} /></label>
        <label className="text-sm font-semibold">Transaction hash<input className={inputClass} value={form.tip_tx_hash} onChange={(e) => update("tip_tx_hash", e.target.value)} /></label>
        <label className="text-sm font-semibold">Amount<input className={inputClass} value={form.amount} onChange={(e) => update("amount", e.target.value)} /></label>
        <label className="text-sm font-semibold">Currency<input className={inputClass} value={form.currency} onChange={(e) => update("currency", e.target.value)} /></label>
        <label className="text-sm font-semibold">Sender wallet<input className={inputClass} value={form.sender_wallet} onChange={(e) => update("sender_wallet", e.target.value)} /></label>
        <label className="text-sm font-semibold">Receiver wallet<input className={inputClass} value={form.receiver_wallet} onChange={(e) => update("receiver_wallet", e.target.value)} /></label>
        <label className="text-sm font-semibold md:col-span-2">Reference<input className={inputClass} value={form.reference} onChange={(e) => update("reference", e.target.value)} /></label>
        <label className="text-sm font-semibold">Tags<input className={inputClass} value={tagsText} onChange={(e) => setTagsText(e.target.value)} /></label>
        <label className="text-sm font-semibold">Metadata JSON<textarea className={`${inputClass} min-h-28 font-mono`} value={metadataText} onChange={(e) => setMetadataText(e.target.value)} /></label>
      </div>
      {error && <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button disabled={busy} onClick={submit} className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-bold text-white disabled:opacity-60">{busy ? "Generating..." : "Generate receipt"}</button>
        <div className="text-sm text-slate-500">If the backend is not reachable, this prototype uses demo mode so the flow still works.</div>
      </div>
    </div>
  );
}
