import Link from 'next/link';

const HOW_STEPS = [
  {
    n: '01',
    title: 'Connect and fund',
    body: 'Connect an EVM wallet, switch to Flare Coston2, get C2FLR gas from the faucet, and claim MockUSDT0 test credits.',
  },
  {
    n: '02',
    title: 'Pay with x402',
    body: 'The app presents an HTTP 402-style payment requirement. Your wallet settles 0.001 MockUSDT0 through the Coston2 x402 facilitator contract.',
  },
  {
    n: '03',
    title: 'Unlock and verify',
    body: 'Settlement is verified on-chain. The research brief unlocks. ProofRails creates an evidence record linking the payment to the resource.',
  },
];

const STATS = [
  { n: '100M+', label: 'x402 transactions' },
  { n: '$617B', label: 'XRPL volume 2025' },
  { n: '$150T', label: 'annual SWIFT flows' },
  { n: '$236M', label: 'Flare TVL peak' },
];

export default function LandingPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-16 space-y-24">

      {/* Hero */}
      <section className="space-y-6 text-center">
        <div className="inline-flex items-center gap-2 bg-navy-800 border border-navy-600 rounded-full px-4 py-1.5 text-xs text-slate-400">
          <span className="status-dot bg-green-400 animate-pulse-slow" />
          Coston2 testnet live
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold text-slate-100 tracking-tight leading-tight">
          Pay.&nbsp;
          <span className="text-accent">Unlock.</span>
          &nbsp;Prove.
        </h1>

        <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Use Flare Coston2 testnet assets to complete an x402 payment, unlock a
          research brief, and receive a verifiable ProofRails receipt.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link href="/unlock" className="btn-primary text-base px-8 py-3.5">
            Start testnet flow
          </Link>
          <Link href="/how-it-works" className="btn-ghost text-base px-6 py-3.5">
            How it works →
          </Link>
        </div>

        <p className="text-xs text-slate-600 max-w-sm mx-auto">
          Coston2 testnet only. No real funds. MockUSDT0 has no market value.
        </p>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {STATS.map(({ n, label }) => (
          <div key={label} className="card text-center">
            <div className="text-2xl font-bold text-accent">{n}</div>
            <div className="text-xs text-slate-500 mt-1">{label}</div>
          </div>
        ))}
      </section>

      {/* What you get */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-slate-100">What you unlock</h2>
        <div className="card bg-navy-900 border-navy-700 flex flex-col sm:flex-row gap-6 items-start">
          <div className="shrink-0 w-16 h-20 bg-navy-700 rounded-lg border border-navy-600 flex items-center justify-center text-slate-500">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-slate-100 text-lg leading-snug">
              Flare x ProofRails: Verifiable Financial Messaging for Onchain Payments
            </p>
            <p className="text-sm text-slate-400">
              A thesis on x402, Flare, ISO 20022-style receipts, and accountable crypto payment
              infrastructure. Includes competitive analysis, real market data, seven builder
              opportunity analyses, and verified Coston2 test evidence.
            </p>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              {['PDF', 'Markdown', '~6,500 words', 'May 2025', 'Coston2 verified'].map(t => (
                <span key={t} className="bg-navy-700 rounded px-2 py-1">{t}</span>
              ))}
            </div>
          </div>
          <div className="shrink-0 text-right sm:ml-auto">
            <div className="text-2xl font-bold text-slate-100">0.001</div>
            <div className="text-xs text-slate-500">MockUSDT0</div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-slate-100">How it works</h2>
        <div className="grid sm:grid-cols-3 gap-5">
          {HOW_STEPS.map(({ n, title, body }) => (
            <div key={n} className="card space-y-3">
              <span className="text-xs font-bold text-accent tracking-widest">{n}</span>
              <h3 className="font-semibold text-slate-100">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Thesis */}
      <section className="card border-navy-600 bg-gradient-to-br from-navy-900 to-navy-800 space-y-4">
        <p className="label">The thesis</p>
        <blockquote className="text-lg text-slate-200 font-medium leading-relaxed">
          "x402 unlocks paid access. Flare settles and verifies programmable payment context.
          ProofRails turns the payment into verifiable financial evidence."
        </blockquote>
        <p className="text-sm text-slate-400">
          A transaction hash proves that value moved. It does not prove what the payment meant.
          No existing crypto payment platform produces ISO 20022-style structured receipts,
          supports x402 natively, and provides a verifiable audit trail. ProofRails is built for
          this scope.
        </p>
        <Link href="/unlock" className="btn-primary inline-block mt-2">
          Start testnet flow
        </Link>
      </section>

    </div>
  );
}
