import type { ReactNode } from 'react';

type DetailRowProps = {
  label: string;
  children: ReactNode;
  className?: string;
};

export function DetailRow({ label, children, className = '' }: DetailRowProps) {
  return (
    <div
      className={`grid grid-cols-1 gap-1 border-b border-white/[0.06] py-3 last:border-0 sm:grid-cols-[minmax(140px,200px)_1fr] sm:gap-6 ${className}`}
    >
      <dt className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-200">{children}</dd>
    </div>
  );
}
