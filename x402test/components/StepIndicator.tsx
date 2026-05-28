'use client';

import clsx from 'clsx';
import type { FlowStep } from '@/hooks/useUnlockFlow';

const STEPS: { id: FlowStep; label: string; short: string }[] = [
  { id: 'connect', label: 'Connect wallet', short: 'Connect' },
  { id: 'network', label: 'Switch to Coston2', short: 'Network' },
  { id: 'gas', label: 'Get C2FLR gas', short: 'Gas' },
  { id: 'token', label: 'Claim MockUSDT0', short: 'Token' },
  { id: 'pay', label: 'Pay with x402', short: 'Pay' },
  { id: 'processing', label: 'Processing', short: 'Processing' },
  { id: 'unlocked', label: 'Unlocked', short: 'Done' },
];

const ORDER: FlowStep[] = ['connect', 'network', 'gas', 'token', 'pay', 'processing', 'unlocked'];

function stepIndex(step: FlowStep) {
  const idx = ORDER.indexOf(step);
  return idx === -1 ? 0 : idx;
}

export function StepIndicator({ current }: { current: FlowStep }) {
  const currentIdx = stepIndex(current === 'error' ? 'pay' : current);

  return (
    <div className="hidden md:flex flex-col gap-1 w-48 shrink-0">
      {STEPS.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <div key={s.id} className="flex items-center gap-3 py-2">
            <div className={clsx(
              'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors',
              done && 'bg-green-500 text-white',
              active && 'bg-accent text-white ring-2 ring-accent/30',
              !done && !active && 'bg-navy-700 text-slate-500',
            )}>
              {done ? '✓' : i + 1}
            </div>
            <span className={clsx(
              'text-sm font-medium transition-colors',
              active && 'text-slate-100',
              done && 'text-green-400',
              !done && !active && 'text-slate-600',
            )}>
              {s.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function MobileStepBar({ current }: { current: FlowStep }) {
  const currentIdx = stepIndex(current === 'error' ? 'pay' : current);
  const pct = Math.round((currentIdx / (STEPS.length - 1)) * 100);

  return (
    <div className="md:hidden mb-6">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Step {currentIdx + 1} of {STEPS.length}</span>
        <span>{STEPS[currentIdx]?.label}</span>
      </div>
      <div className="h-1 bg-navy-700 rounded-full">
        <div
          className="h-1 bg-accent rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
