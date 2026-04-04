import { NavLink } from 'react-router-dom';

const nav = [
  { to: '/records', label: 'Records' },
  { to: '/verify', label: 'Verify' },
  { to: '/settings', label: 'Settings' },
];

const linkClass =
  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150';

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[260px] flex-col border-r border-white/[0.08] bg-[var(--color-surface-1)]/95 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-2 border-b border-white/[0.06] px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-500/30 bg-gradient-to-br from-cyan-500/20 to-transparent text-sm font-bold text-cyan-200 shadow-[0_0_20px_rgba(34,211,238,0.12)]">
          PR
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-slate-100">ProofRails</p>
          <p className="text-[11px] text-slate-500">Evidence layer</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `${linkClass} ${
                isActive
                  ? 'border border-cyan-500/25 bg-cyan-500/10 text-cyan-50 shadow-[0_0_24px_rgba(34,211,238,0.08)]'
                  : 'border border-transparent text-slate-400 hover:border-white/[0.06] hover:bg-white/[0.04] hover:text-slate-200'
              }`
            }
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current opacity-60" aria-hidden />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/[0.06] p-4">
        <p className="text-[11px] leading-relaxed text-slate-600">
          XRP · FXRP payment activity → Proof Records
        </p>
      </div>
    </aside>
  );
}
