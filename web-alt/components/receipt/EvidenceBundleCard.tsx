import { Copy, ExternalLink } from "lucide-react";
import type { Receipt } from "../../lib/proofrails";
import { explorerTxUrl, shortHash } from "../../lib/proofrails";

function copy(value?: string) {
  if (value) navigator.clipboard?.writeText(value).catch(() => undefined);
}

export default function EvidenceBundleCard({ receipt }: { receipt: Receipt }) {
  const txUrl = explorerTxUrl(receipt.flare_txid);
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-black tracking-tight">Evidence bundle</h2>
      <p className="mt-2 text-sm text-slate-600">The bundle packages receipt metadata, ISO-style artifacts, checksums, and anchor references. Verification compares the bundle hash against the onchain anchor.</p>
      <div className="mt-5 space-y-3">
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Bundle hash</div>
          <div className="mt-2 flex items-center justify-between gap-3 font-mono text-sm"><span className="break-all">{receipt.bundle_hash || "Pending"}</span><button onClick={() => copy(receipt.bundle_hash)} className="rounded-lg border px-2 py-1 text-slate-600"><Copy className="h-4 w-4" /></button></div>
        </div>
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Anchor transaction</div>
          <div className="mt-2 flex items-center justify-between gap-3 font-mono text-sm"><span>{shortHash(receipt.flare_txid)}</span>{txUrl && <a href={txUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-slate-700">Explorer <ExternalLink className="h-3 w-3" /></a>}</div>
        </div>
      </div>
      {receipt.bundle_url && <a href={receipt.bundle_url} className="mt-5 inline-flex rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white">Download evidence bundle</a>}
    </section>
  );
}
