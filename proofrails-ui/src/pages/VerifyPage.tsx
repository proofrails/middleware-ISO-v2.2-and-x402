import { useState } from 'react';
import { mockRecords } from '../data/mockRecords';
import { PageContainer } from '../components/layout/PageContainer';
import { ActionButton } from '../components/ui/ActionButton';
import { Card } from '../components/ui/Card';
import { HashField } from '../components/ui/HashField';
import { StatusBadge } from '../components/ui/StatusBadge';

const inputClass =
  'mt-1 w-full rounded-lg border border-white/10 bg-[var(--color-surface-2)] px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30';

export function VerifyPage() {
  const [recordOrBundle, setRecordOrBundle] = useState('');
  const [bundleUrl, setBundleUrl] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<null | {
    ok: boolean;
    matched: boolean;
    bundleHash: string;
    flareTx: string;
    at: string;
    details: string;
    note: string;
  }>(null);

  const handleRun = () => {
    setRunning(true);
    setResult(null);
    window.setTimeout(() => {
      const match = mockRecords.find(
        (r) =>
          r.id === recordOrBundle.trim() ||
          r.evidenceBundleHash.toLowerCase() === recordOrBundle.trim().toLowerCase(),
      );
      const ok = match !== undefined && match.verificationStatus === 'Verified';
      setResult({
        ok,
        matched: Boolean(match?.flareTxHash && match.flareTxHash !== '—'),
        bundleHash: match?.evidenceBundleHash ?? '0x… (unknown)',
        flareTx: match?.flareTxHash ?? '—',
        at: new Date().toISOString(),
        details: ok
          ? 'Digest match · anchor commitment valid · ISO lineage checks passed.'
          : match
            ? 'Bundle found but verification state is not Verified. Re-run anchor or resolve exceptions.'
            : 'No Proof Record or bundle hash matched in this workspace.',
        note:
          'Technical: verification uses canonical SHA-256 over the sealed manifest plus registry merkle proof (demo).',
      });
      setRunning(false);
    }, 1200);
  };

  return (
    <PageContainer>
      <div className="mx-auto max-w-3xl">
        <p className="mb-8 text-center text-sm text-slate-500">
          Independently confirm that a Proof Record&apos;s evidence bundle matches its Flare anchor.
        </p>

        <Card padding="lg">
          <h2 className="text-lg font-semibold text-slate-100">Run verification</h2>
          <p className="mt-1 text-sm text-slate-500">
            Enter a Proof Record ID or evidence bundle hash. Optional bundle URL for out-of-band
            packages.
          </p>
          <div className="mt-6 space-y-4">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Proof Record ID or bundle hash
              </label>
              <input
                className={`${inputClass} font-mono text-[13px]`}
                value={recordOrBundle}
                onChange={(e) => setRecordOrBundle(e.target.value)}
                placeholder="PR-2026-… or 0x…"
              />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Bundle URL (optional)
              </label>
              <input
                className={inputClass}
                value={bundleUrl}
                onChange={(e) => setBundleUrl(e.target.value)}
                placeholder="https://storage…/bundle.tar.gz"
              />
            </div>
            <ActionButton variant="primary" disabled={running} onClick={handleRun}>
              {running ? 'Running verification…' : 'Run Verification'}
            </ActionButton>
          </div>
        </Card>

        {result ? (
          <Card className="mt-6" padding="lg">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge kind="verification" value={result.ok ? 'Verified' : 'Failed'} />
              <span className="text-sm text-slate-500">
                Matched on Flare:{' '}
                <span className="font-medium text-slate-300">{result.matched ? 'Yes' : 'No'}</span>
              </span>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <HashField label="Bundle hash" value={result.bundleHash} />
              <HashField label="Flare tx hash" value={result.flareTx} />
            </div>
            <p className="mt-4 font-mono text-[11px] text-slate-600">{result.at}</p>
            <p className="mt-4 text-sm text-slate-300">{result.details}</p>
            <div className="mt-6 rounded-lg border border-white/[0.06] bg-[var(--color-surface-1)]/80 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Technical notes
              </p>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">{result.note}</p>
            </div>
          </Card>
        ) : null}
      </div>
    </PageContainer>
  );
}
