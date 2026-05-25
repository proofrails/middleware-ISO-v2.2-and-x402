import Link from "next/link";
import { ArrowRight, CheckCircle2, FileArchive, FileText, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 p-8 text-white shadow-xl md:p-12">
        <div className="max-w-3xl">
          <div className="mb-4 inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-sm font-semibold text-pink-100">Transaction hash to verifiable receipt</div>
          <h1 className="text-5xl font-black tracking-tight md:text-7xl">Verifiable receipts for onchain payments.</h1>
          <p className="mt-6 max-w-2xl text-lg text-slate-300">Paste a transaction, add payment context, and ProofRails generates a finance-readable receipt with ISO-style artifacts, an evidence bundle, and an onchain hash anchor.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/create" className="inline-flex items-center gap-2 rounded-2xl bg-white px-5 py-3 font-black text-slate-950">Create receipt <ArrowRight className="h-4 w-4" /></Link>
            <Link href="/verify" className="inline-flex items-center gap-2 rounded-2xl border border-white/20 px-5 py-3 font-black text-white">Verify receipt</Link>
          </div>
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-4">
        {[{icon:FileText,title:"1. Record",body:"Enter the payment reference and business context."},{icon:FileArchive,title:"2. Package",body:"Generate ISO-style artifacts and an evidence bundle."},{icon:ShieldCheck,title:"3. Anchor",body:"Commit the bundle hash onchain for later verification."},{icon:CheckCircle2,title:"4. Verify",body:"Share a public page that explains what was verified."}].map((item)=>{const Icon=item.icon;return <div key={item.title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><Icon className="h-7 w-7 text-pink-600"/><h2 className="mt-4 text-lg font-black">{item.title}</h2><p className="mt-2 text-sm text-slate-600">{item.body}</p></div>})}
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-black tracking-tight">What ProofRails verifies</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl bg-emerald-50 p-5"><div className="font-black text-emerald-950">Verified</div><p className="mt-2 text-sm text-emerald-900">Evidence integrity, bundle hash consistency, and onchain anchor match when an anchor exists.</p></div>
          <div className="rounded-2xl bg-slate-50 p-5"><div className="font-black text-slate-950">Not claimed</div><p className="mt-2 text-sm text-slate-700">Invoice validity, KYC status, legal settlement finality, sender intent, or bank acceptance.</p></div>
        </div>
      </section>
    </div>
  );
}
