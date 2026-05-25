"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import ReceiptStatusBadge from "../../components/receipt/ReceiptStatusBadge";
import { listReceipts, shortHash, type Receipt } from "../../lib/proofrails";

export default function ReceiptsPage() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [source, setSource] = useState<"backend" | "demo">("demo");
  useEffect(() => { listReceipts().then((r) => { setReceipts(r.items); setSource(r.source); }); }, []);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="text-4xl font-black tracking-tight">Receipts</h1><p className="mt-2 text-slate-600">Every payment record, evidence bundle, and verification state in one place.</p></div>
        <Link href="/create" className="rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white">Create receipt</Link>
      </div>
      {source === "demo" && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Demo mode is active because the backend is not reachable from this browser session.</div>}
      <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        {receipts.length === 0 ? <div className="p-8 text-slate-600">No receipts yet. Create the first one to see the flow.</div> : receipts.map((r) => (
          <Link href={`/receipts/${r.id}`} key={r.id} className="grid gap-3 border-b border-slate-100 p-5 hover:bg-slate-50 md:grid-cols-[1fr_150px_170px_140px]">
            <div><div className="font-black">{r.reference || r.id}</div><div className="mt-1 font-mono text-xs text-slate-500">{shortHash(r.tip_tx_hash)}</div></div>
            <div className="text-sm font-semibold">{r.amount} {r.currency}</div>
            <ReceiptStatusBadge status={r.status} />
            <div className="text-sm text-slate-500">{new Date(r.created_at).toLocaleDateString()}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
