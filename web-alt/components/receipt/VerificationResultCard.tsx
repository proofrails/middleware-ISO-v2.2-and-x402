import { AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import type { VerificationResult } from "../../lib/proofrails";
import { shortHash } from "../../lib/proofrails";

export default function VerificationResultCard({ result }: { result: VerificationResult }) {
  const verified = result.status === "verified";
  const pending = result.status === "pending";
  return (
    <section className={`rounded-3xl border p-6 shadow-sm ${verified ? "border-emerald-200 bg-emerald-50" : pending ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"}`}>
      <div className="flex items-center gap-3">
        {verified ? <CheckCircle2 className="h-7 w-7 text-emerald-700" /> : pending ? <Clock className="h-7 w-7 text-amber-700" /> : <AlertTriangle className="h-7 w-7 text-red-700" />}
        <div>
          <h2 className="text-xl font-black tracking-tight">{verified ? "Verified receipt" : pending ? "Verification pending" : "Verification failed"}</h2>
          <p className="text-sm text-slate-700">{verified ? "The evidence bundle hash matches the onchain anchor." : pending ? "Evidence exists, but the anchor is not final yet." : "ProofRails could not match the evidence to an anchor."}</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl bg-white/70 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Bundle hash</div><div className="mt-1 font-mono text-sm">{shortHash(result.bundle_hash)}</div></div>
        <div className="rounded-2xl bg-white/70 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">Anchor tx</div><div className="mt-1 font-mono text-sm">{shortHash(result.flare_txid)}</div></div>
      </div>
      <div className="mt-5 rounded-2xl bg-white/70 p-4 text-sm text-slate-700">
        <div className="font-bold text-slate-950">What this proves</div>
        <p className="mt-1">ProofRails verifies evidence integrity and anchor consistency. It does not automatically prove invoice validity, KYC status, sender intent, legal settlement finality, or bank acceptance.</p>
      </div>
      {result.errors.length > 0 && <div className="mt-4 text-sm text-red-800">{result.errors.join(" ")}</div>}
    </section>
  );
}
