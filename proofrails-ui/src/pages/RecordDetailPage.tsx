import { Link, useNavigate, useParams } from 'react-router-dom';
import { getRecordById } from '../data/mockRecords';
import { PageContainer } from '../components/layout/PageContainer';
import { ActionButton } from '../components/ui/ActionButton';
import { Card } from '../components/ui/Card';
import { DetailRow } from '../components/ui/DetailRow';
import { HashField } from '../components/ui/HashField';
import { SectionHeader } from '../components/ui/SectionHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useToast } from '../context/ToastContext';

function formatWhen(iso: string) {
  if (iso === '—') return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      dateStyle: 'full',
      timeStyle: 'long',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function RecordDetailPage() {
  const { recordId } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const id = recordId ? decodeURIComponent(recordId) : '';
  const record = id ? getRecordById(id) : undefined;

  if (!record) {
    return (
      <PageContainer>
        <Card>
          <h2 className="text-lg font-semibold text-slate-100">Proof Record not found</h2>
          <p className="mt-2 text-sm text-slate-500">
            No Proof Record matches this identifier in the current workspace.
          </p>
          <ActionButton variant="secondary" className="mt-6" onClick={() => navigate('/records')}>
            Back to Proof Records
          </ActionButton>
        </Card>
      </PageContainer>
    );
  }

  const explorerUrl =
    record.flareTxHash && record.flareTxHash !== '—'
      ? `https://coston2-explorer.flare.network/tx/${record.flareTxHash}`
      : undefined;

  return (
    <PageContainer>
      <div className="mb-6">
        <Link
          to="/records"
          className="text-sm text-cyan-400/90 hover:text-cyan-300 transition-colors"
        >
          ← Proof Records
        </Link>
      </div>

      <Card padding="lg" className="mb-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge kind="status" value={record.status} />
              <StatusBadge kind="anchor" value={record.anchorStatus} />
              <StatusBadge kind="verification" value={record.verificationStatus} />
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                Proof Record ID
              </p>
              <code className="mt-1 block break-all font-mono text-lg font-medium text-cyan-100 sm:text-xl">
                {record.id}
              </code>
            </div>
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="text-2xl font-semibold tabular-nums text-slate-50">
                {record.amount}
              </span>
              <span className="text-lg font-medium text-slate-400">{record.asset}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
              <code className="font-mono text-[12px] text-cyan-100/80">{record.sender}</code>
              <span className="text-slate-600">→</span>
              <code className="font-mono text-[12px] text-cyan-100/80">{record.receiver}</code>
            </div>
            <p className="text-sm text-slate-400">
              <span className="text-slate-500">Reference: </span>
              {record.reference}
            </p>
            <p className="text-xs text-slate-600">Created {formatWhen(record.createdAt)}</p>
          </div>
          <div className="flex flex-shrink-0 flex-wrap gap-2 lg:flex-col lg:items-stretch">
            <ActionButton
              variant="primary"
              onClick={() => showToast('Verification queued for this Proof Record.')}
            >
              Verify
            </ActionButton>
            <ActionButton
              variant="secondary"
              onClick={() => showToast('Evidence bundle export started.')}
            >
              Export Bundle
            </ActionButton>
            <ActionButton
              variant="secondary"
              onClick={() => showToast('ISO artifact package downloaded.')}
            >
              Export ISO
            </ActionButton>
            <ActionButton
              variant="secondary"
              onClick={() => showToast('JSON record copied to clipboard.')}
            >
              Export JSON
            </ActionButton>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHeader
            title="Payment Summary"
            description="Normalized view of the captured payment event and business metadata."
          />
          <dl>
            <DetailRow label="Source type">{record.sourceType}</DetailRow>
            <DetailRow label="Source tx hash">
              <HashField value={record.sourceTxHash} truncate={false} />
            </DetailRow>
            <DetailRow label="Source environment">{record.sourceEnvironment}</DetailRow>
            <DetailRow label="Payment status">{record.paymentStatus}</DetailRow>
            <DetailRow label="Asset">{record.asset}</DetailRow>
            <DetailRow label="Amount">
              <span className="tabular-nums">{record.amount}</span>
            </DetailRow>
            <DetailRow label="Sender">
              <code className="font-mono text-[12px] text-cyan-100/85">{record.sender}</code>
            </DetailRow>
            <DetailRow label="Receiver">
              <code className="font-mono text-[12px] text-cyan-100/85">{record.receiver}</code>
            </DetailRow>
            <DetailRow label="Counterparty">{record.counterparty}</DetailRow>
            <DetailRow label="Purpose">{record.purpose}</DetailRow>
            <DetailRow label="Tags">
              <div className="flex flex-wrap gap-2">
                {record.tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-0.5 text-xs text-slate-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </DetailRow>
          </dl>
        </Card>

        <Card>
          <SectionHeader
            title="Evidence and Verification"
            description="Integrity of the evidence bundle and its relationship to policy checks."
          />
          <dl>
            <DetailRow label="Evidence bundle hash">
              <HashField value={record.evidenceBundleHash} truncate={false} />
            </DetailRow>
            <DetailRow label="Bundle status">
              <StatusBadge kind="status" value={record.bundleStatus} />
            </DetailRow>
            <DetailRow label="Verification status">
              <StatusBadge kind="verification" value={record.verificationStatus} />
            </DetailRow>
            <DetailRow label="Last verified at">{record.lastVerifiedAt}</DetailRow>
            <DetailRow label="Verification details">
              <span className="text-slate-400">{record.verificationDetails}</span>
            </DetailRow>
          </dl>
          <div className="mt-6 border-t border-white/[0.06] pt-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Processing timeline
            </p>
            <ul className="space-y-3">
              {record.timeline.map((ev) => (
                <li
                  key={ev.id}
                  className="flex gap-3 rounded-lg border border-white/[0.06] bg-[var(--color-surface-1)]/60 px-3 py-2.5"
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      ev.state === 'done'
                        ? 'bg-teal-400'
                        : ev.state === 'current'
                          ? 'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.5)]'
                          : ev.state === 'error'
                            ? 'bg-rose-400'
                            : 'bg-slate-600'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-200">{ev.label}</p>
                    <p className="text-xs text-slate-500">{ev.detail}</p>
                    <p className="mt-1 font-mono text-[11px] text-slate-600">{ev.at}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Flare Anchor"
            description="On-chain commitment for tamper-evident reconciliation."
            action={
              record.anchorStatus === 'Failed' ? (
                <ActionButton
                  variant="secondary"
                  onClick={() => showToast('Anchor retry submitted to queue.')}
                >
                  Retry anchor
                </ActionButton>
              ) : undefined
            }
          />
          <dl>
            <DetailRow label="Anchor status">
              <StatusBadge kind="anchor" value={record.anchorStatus} />
            </DetailRow>
            <DetailRow label="Flare tx hash">
              {record.flareTxHash === '—' ? (
                <span className="text-slate-500">—</span>
              ) : (
                <HashField value={record.flareTxHash} truncate={false} />
              )}
            </DetailRow>
            <DetailRow label="Anchored at">{record.anchoredAt}</DetailRow>
          </dl>
          {explorerUrl ? (
            <a
              href={explorerUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex text-sm font-medium text-cyan-400 hover:text-cyan-300"
            >
              View on explorer →
            </a>
          ) : null}
        </Card>

        <Card>
          <SectionHeader
            title="Artifacts"
            description="Exportable outputs for operations, audit, and counterparty packets."
          />
          <ul className="space-y-3">
            {record.artifacts.length === 0 ? (
              <li className="text-sm text-slate-500">No artifacts available yet.</li>
            ) : (
              record.artifacts.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-col gap-3 rounded-lg border border-white/[0.08] bg-[var(--color-surface-1)]/50 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-slate-100">{a.name}</p>
                    <p className="mt-0.5 text-sm text-slate-500">{a.description}</p>
                    <p className="mt-2 text-[11px] text-slate-600">
                      {a.format}
                      {a.updatedAt !== '—' ? ` · Updated ${a.updatedAt}` : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton variant="ghost" className="text-xs" onClick={() => showToast('Preview opened (demo).')}>
                      View
                    </ActionButton>
                    <ActionButton
                      variant="secondary"
                      className="text-xs"
                      onClick={() => showToast(`${a.name} download started.`)}
                    >
                      Download
                    </ActionButton>
                    <ActionButton
                      variant="secondary"
                      className="text-xs"
                      onClick={() => showToast('Signed URL copied.')}
                    >
                      Copy link
                    </ActionButton>
                  </div>
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>
    </PageContainer>
  );
}
