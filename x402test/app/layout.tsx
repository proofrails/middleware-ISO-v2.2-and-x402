import type { Metadata } from 'next';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'ProofRails x402 Testnet — Pay. Unlock. Prove.',
  description:
    'Use Flare Coston2 testnet assets to complete an x402 payment, unlock a research brief, and receive a verifiable ProofRails receipt.',
  openGraph: {
    title: 'ProofRails x402 Testnet',
    description: 'Pay. Unlock. Prove. — A guided x402 payment demo on Flare Coston2.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <header className="border-b border-navy-800 bg-navy-950/80 backdrop-blur-sm sticky top-0 z-50">
            <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2 group">
                <span className="text-accent font-bold tracking-tight text-sm">ProofRails</span>
                <span className="text-navy-600 text-sm">/</span>
                <span className="text-slate-400 text-sm font-medium group-hover:text-slate-200 transition-colors">
                  x402 Testnet
                </span>
              </a>
              <nav className="flex items-center gap-4 text-sm">
                <a href="/how-it-works" className="text-slate-500 hover:text-slate-200 transition-colors">
                  How it works
                </a>
                <a
                  href="https://app.proofrails.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-500 hover:text-slate-200 transition-colors"
                >
                  Main app ↗
                </a>
              </nav>
            </div>
          </header>
          <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>
          <footer className="border-t border-navy-800 mt-16 py-8">
            <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
              <div>
                Coston2 testnet only. MockUSDT0 and C2FLR have no real value.
              </div>
              <div className="flex items-center gap-4">
                <a href="https://app.proofrails.com" target="_blank" rel="noopener noreferrer" className="hover:text-slate-400 transition-colors">
                  app.proofrails.com
                </a>
                <a href="https://coston2-explorer.flare.network" target="_blank" rel="noopener noreferrer" className="hover:text-slate-400 transition-colors">
                  Explorer ↗
                </a>
              </div>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
