"use client";
import { Copy } from "lucide-react";
import type { Receipt } from "../../lib/proofrails";

export default function ShareReceiptPanel({ receipt }: { receipt: Receipt }) {
  const url = typeof window !== "undefined" ? `${window.location.origin}/verify/${receipt.id}` : `/verify/${receipt.id}`;
  return (
    <section className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
      <h2 className="text-xl font-black tracking-tight">Shareable verification link</h2>
      <p className="mt-2 text-sm text-slate-300">Send this to a user, customer, auditor, partner, or investor. They can verify the receipt without using the dashboard.</p>
      <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl bg-white/10 p-3">
        <div className="min-w-0 flex-1 break-all font-mono text-sm text-slate-100">{url}</div>
        <button onClick={() => navigator.clipboard?.writeText(url)} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-slate-950"><Copy className="h-4 w-4" /> Copy</button>
      </div>
    </section>
  );
}
