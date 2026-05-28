import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const variants: Record<Variant, string> = {
  primary:
    'border border-cyan-500/40 bg-gradient-to-b from-cyan-500/20 to-cyan-600/10 text-cyan-50 shadow-[0_0_20px_rgba(34,211,238,0.15)] hover:from-cyan-500/30 hover:to-cyan-600/15',
  secondary:
    'border border-white/12 bg-white/[0.04] text-slate-100 hover:border-white/18 hover:bg-white/[0.07]',
  ghost: 'border border-transparent text-slate-300 hover:bg-white/[0.05] hover:text-slate-100',
  danger:
    'border border-rose-500/35 bg-rose-500/10 text-rose-100 hover:bg-rose-500/15',
};

export function ActionButton({
  variant = 'secondary',
  className = '',
  children,
  ...props
}: ActionButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-150 disabled:pointer-events-none disabled:opacity-40 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
