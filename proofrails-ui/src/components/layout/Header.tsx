import { NavLink, useLocation } from 'react-router-dom';
import { getPageTitle } from '../../lib/pageTitle';

const workspaces = ['Acme Treasury Ops', 'Nordic Custody — Production', 'Helios SPV — Sandbox'];

export function Header() {
  const { pathname } = useLocation();
  const title = getPageTitle(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-white/[0.08] bg-[var(--color-surface-0)]/85 px-6 backdrop-blur-md lg:px-10">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold tracking-tight text-slate-50">{title}</h1>
      </div>
      <div className="hidden items-center gap-3 md:flex">
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </span>
          <input
            type="search"
            placeholder="Search Proof Records…"
            className="h-10 w-[220px] rounded-lg border border-white/10 bg-[var(--color-surface-2)] pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 lg:w-[280px]"
            readOnly
            aria-label="Search (demo)"
          />
        </div>
        <select
          className="h-10 max-w-[200px] cursor-pointer truncate rounded-lg border border-white/10 bg-[var(--color-surface-2)] px-3 text-sm text-slate-200 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
          defaultValue={workspaces[0]}
          aria-label="Workspace"
        >
          {workspaces.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-3">
        <NavLink
          to="/docs"
          className={({ isActive }) =>
            `flex h-10 items-center rounded-lg border px-3 text-sm transition ${
              isActive
                ? 'border-cyan-500/35 bg-cyan-500/10 text-cyan-50'
                : 'border-white/10 bg-[var(--color-surface-2)] text-slate-300 hover:border-cyan-500/25 hover:text-slate-100'
            }`
          }
        >
          Docs
        </NavLink>
        <div className="flex h-10 items-center gap-2 rounded-lg border border-white/10 bg-[var(--color-surface-2)] pl-2 pr-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-slate-600 to-slate-800 text-xs font-semibold text-slate-200">
            VM
          </div>
          <div className="hidden text-left leading-tight sm:block">
            <p className="text-xs font-medium text-slate-200">Victor Munoz</p>
            <p className="text-[10px] text-slate-500">Operator</p>
          </div>
        </div>
      </div>
    </header>
  );
}
