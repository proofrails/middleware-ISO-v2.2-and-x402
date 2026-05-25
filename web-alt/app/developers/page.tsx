export default function DevelopersPage() {
  return (
    <div className="space-y-6">
      <div><h1 className="text-4xl font-black tracking-tight">Developers</h1><p className="mt-2 text-slate-600">Integrate the core receipt flow first. Everything else builds on this path.</p></div>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-2xl font-black">Core API flow</h2><pre className="mt-4 overflow-auto rounded-2xl bg-slate-950 p-5 text-sm text-slate-100">{`POST /v1/iso/record-tip
GET  /v1/operations/{operation_id}
GET  /v1/iso/receipts/{receipt_id}
GET  /v1/iso/messages/{receipt_id}
POST /v1/iso/verify`}</pre></section>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-2xl font-black">Positioning rule</h2><p className="mt-2 text-slate-600">Use ISO-style artifacts unless a stricter compliance claim has been independently verified. ProofRails records, packages, anchors, and verifies evidence around payments. It does not move funds.</p></section>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-2xl font-black">Labs</h2><p className="mt-2 text-slate-600">x402, agents, FDC, FAssets, and XRPL Smart Accounts belong after the receipt flow works cleanly. Keep unfinished flows out of the primary product promise.</p></section>
    </div>
  );
}
