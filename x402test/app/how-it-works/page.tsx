import Link from 'next/link';

const STEPS = [
  {
    n: 1,
    title: 'Connect wallet',
    detail: 'Connect an EVM-compatible wallet (MetaMask, Coinbase Wallet, etc.) using EIP-1193. No account registration required.',
  },
  {
    n: 2,
    title: 'Switch to Flare Coston2',
    detail: 'The app prompts you to switch to or add Flare Coston2 (Chain ID 114). The network config is added automatically if not already in your wallet.',
  },
  {
    n: 3,
    title: 'Get C2FLR gas',
    detail: 'You need a small amount of C2FLR (Coston2 native token) for transaction fees. The app links you to the Coston2 faucet and polls your balance until funded.',
  },
  {
    n: 4,
    title: 'Claim MockUSDT0',
    detail: 'MockUSDT0 is a test token deployed on Coston2 that mimics the USDT0 payment flow. You mint 1.0 MockUSDT0 directly from the contract. The payment requires 0.001.',
  },
  {
    n: 5,
    title: 'Pay with x402',
    detail: 'The app constructs an x402/EIP-3009-style payment payload and calls the X402Facilitator contract. The facilitator verifies the payload, settles the transfer, and records the payment on-chain.',
  },
  {
    n: 6,
    title: 'Backend verification',
    detail: 'After settlement, the x402test backend independently verifies the settlement transaction on Coston2. It checks the facilitator record, confirms payer, recipient, token, and amount. The backend never trusts client-submitted values.',
  },
  {
    n: 7,
    title: 'Resource unlock',
    detail: 'After verification, the backend issues a short-lived signed access token. The research brief (PDF and Markdown) becomes available for download or web reading.',
  },
  {
    n: 8,
    title: 'ProofRails receipt',
    detail: 'The backend creates a ProofRails receipt record linking the payment to the resource. The receipt includes payer, payee, token, amount, settlement hash, payment purpose, and a verifiable evidence bundle. You can verify it at app.proofrails.com.',
  },
];

export default function HowItWorksPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16 space-y-12">
      <div className="space-y-3">
        <h1 className="text-3xl font-bold text-slate-100">How it works</h1>
        <p className="text-slate-400 text-lg">
          A step-by-step walkthrough of the Coston2 x402 testnet flow.
        </p>
      </div>

      <div className="space-y-4">
        {STEPS.map(({ n, title, detail }) => (
          <div key={n} className="card flex gap-5">
            <div className="w-9 h-9 rounded-full bg-navy-700 border border-navy-600 flex items-center justify-center text-sm font-bold text-accent shrink-0 mt-0.5">
              {n}
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 mb-1">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{detail}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="card bg-navy-800/50 border-navy-600 space-y-3">
        <p className="label">Important caveats</p>
        <ul className="text-sm text-slate-400 space-y-2 list-none">
          <li className="flex gap-2"><span className="text-amber-500 shrink-0">!</span> This is Coston2 testnet only. MockUSDT0 and C2FLR have no real value.</li>
          <li className="flex gap-2"><span className="text-amber-500 shrink-0">!</span> The deployed MockUSDT0 does not enforce real EIP-712 signature recovery. This is acceptable for the Coston2 UX test but not representative of production token security.</li>
          <li className="flex gap-2"><span className="text-amber-500 shrink-0">!</span> This demo does not claim to prove production USDT0 settlement or production-grade EIP-3009 enforcement.</li>
        </ul>
      </div>

      <div className="flex gap-4">
        <Link href="/unlock" className="btn-primary">Start testnet flow</Link>
        <Link href="/" className="btn-secondary">Back to home</Link>
      </div>
    </div>
  );
}
