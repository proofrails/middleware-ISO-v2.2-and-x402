import type { ReactNode } from 'react';

type CardProps = {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
};

const pad = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function Card({ children, className = '', padding = 'md' }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-white/[0.08] bg-[var(--color-surface-2)]/80 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)] backdrop-blur-sm transition-shadow duration-200 hover:shadow-[0_0_0_1px_rgba(34,211,238,0.06),0_8px_40px_-12px_rgba(0,0,0,0.5)] ${pad[padding]} ${className}`}
    >
      {children}
    </div>
  );
}
