import type { ReactNode } from 'react';

type FilterBarProps = {
  children: ReactNode;
  className?: string;
};

export function FilterBar({ children, className = '' }: FilterBarProps) {
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border border-white/[0.08] bg-[var(--color-surface-1)]/90 p-4 backdrop-blur-sm lg:flex-row lg:flex-wrap lg:items-end ${className}`}
    >
      {children}
    </div>
  );
}

type FilterFieldProps = {
  label: string;
  children: ReactNode;
  className?: string;
};

export function FilterField({ label, children, className = '' }: FilterFieldProps) {
  return (
    <div className={`min-w-[160px] flex-1 ${className}`}>
      <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
        {label}
      </label>
      {children}
    </div>
  );
}
