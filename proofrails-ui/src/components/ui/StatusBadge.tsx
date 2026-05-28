import type { AnchorStatus, RecordStatus, VerificationStatus } from '../../types/record';

type BadgeKind = 'status' | 'anchor' | 'verification';

type StatusBadgeProps = {
  kind: BadgeKind;
  value: RecordStatus | AnchorStatus | VerificationStatus | string;
};

const statusStyles: Record<string, string> = {
  Pending: 'border-amber-500/35 bg-amber-500/10 text-amber-200',
  Processing: 'border-sky-500/35 bg-sky-500/10 text-sky-200',
  Complete: 'border-emerald-500/35 bg-emerald-500/10 text-emerald-200',
  Failed: 'border-rose-500/40 bg-rose-500/10 text-rose-200',
  Anchored: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
  Verified: 'border-teal-500/40 bg-teal-500/10 text-teal-200',
  Unverified: 'border-slate-500/40 bg-slate-500/10 text-slate-300',
  Building: 'border-sky-500/35 bg-sky-500/10 text-sky-200',
  Sealed: 'border-teal-500/35 bg-teal-500/10 text-teal-200',
  Ready: 'border-emerald-500/35 bg-emerald-500/10 text-emerald-200',
  Invalid: 'border-rose-500/40 bg-rose-500/10 text-rose-200',
  Queued: 'border-slate-500/40 bg-slate-500/10 text-slate-300',
};

function classFor(value: string): string {
  return statusStyles[value] ?? 'border-white/15 bg-white/5 text-slate-200';
}

export function StatusBadge({ kind, value }: StatusBadgeProps) {
  const label =
    kind === 'anchor' ? 'Anchor' : kind === 'verification' ? 'Verification' : 'Status';
  return (
    <span
      role="status"
      aria-label={`${label}: ${value}`}
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium tracking-wide ${classFor(String(value))}`}
    >
      {value}
    </span>
  );
}
