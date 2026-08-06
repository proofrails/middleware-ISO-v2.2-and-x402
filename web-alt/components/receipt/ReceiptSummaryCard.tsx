import type { Receipt } from "../../lib/proofrails";
import { shortHash } from "../../lib/proofrails";
import ReceiptStatusBadge from "./ReceiptStatusBadge";

export default function ReceiptSummaryCard({ receipt }: { receipt: Receipt }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-slate-500">Receipt</div>
          <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">{receipt.reference || receipt.id}</h1>
        </div>
        <ReceiptStatusBadge status={receipt.status} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Amount</div><div className="mt-1 text-xl font-bold">{receipt.amount || "-"} {receipt.currency || ""}</div></div>
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Chain</div><div className="mt-1 text-xl font-bold capitalize">{receipt.chain || "flare"}</div></div>
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Transaction</div><div className="mt-1 font-mono text-sm">{shortHash(receipt.tip_tx_hash)}</div></div>
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Sender</div><div className="mt-1 font-mono text-sm">{shortHash(receipt.sender_wallet)}</div></div>
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Receiver</div><div className="mt-1 font-mono text-sm">{shortHash(receipt.receiver_wallet)}</div></div>
        <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Created</div><div className="mt-1 text-sm font-semibold">{new Date(receipt.created_at).toLocaleString()}</div></div>
      </div>
    </section>
  );
}
