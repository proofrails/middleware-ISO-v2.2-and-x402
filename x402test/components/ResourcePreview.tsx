'use client';

export function ResourcePreview() {
  return (
    <div className="bg-navy-800 border border-navy-600 rounded-xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="label mb-1">Gated research brief</p>
          <h3 className="font-semibold text-slate-100 leading-snug">
            Flare x ProofRails: Verifiable Financial Messaging for Onchain Payments
          </h3>
        </div>
        <div className="shrink-0 bg-navy-700 rounded-lg p-2 text-slate-500">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
      </div>
      <p className="text-sm text-slate-400">
        A thesis on x402, Flare, ISO 20022-style receipts, and accountable crypto payment
        infrastructure. Includes competitive analysis, real market data, builder opportunities,
        and verified Coston2 test evidence.
      </p>
      <div className="flex gap-3 text-xs text-slate-500">
        <span className="bg-navy-700 rounded px-2 py-1">PDF</span>
        <span className="bg-navy-700 rounded px-2 py-1">Markdown</span>
        <span className="bg-navy-700 rounded px-2 py-1">~6,500 words</span>
        <span className="bg-navy-700 rounded px-2 py-1">May 2025</span>
      </div>
    </div>
  );
}
