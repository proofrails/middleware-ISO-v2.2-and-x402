import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockRecords } from '../data/mockRecords';
import type { ProofRecord } from '../types/record';
import { PageContainer } from '../components/layout/PageContainer';
import { ActionButton } from '../components/ui/ActionButton';
import { DataTable, type Column } from '../components/ui/DataTable';
import { FilterBar, FilterField } from '../components/ui/FilterBar';
import { StatusBadge } from '../components/ui/StatusBadge';

function formatWhen(iso: string) {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function shortId(id: string) {
  if (id.length <= 24) return id;
  return `${id.slice(0, 14)}…${id.slice(-6)}`;
}

export function RecordsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [assetFilter, setAssetFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = window.setTimeout(() => setLoading(false), 480);
    return () => window.clearTimeout(t);
  }, []);

  const filtered = useMemo(() => {
    return mockRecords.filter((r) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        r.id.toLowerCase().includes(q) ||
        r.reference.toLowerCase().includes(q) ||
        r.sourceTxHash.toLowerCase().includes(q);
      const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
      const matchesAsset = assetFilter === 'all' || r.asset === assetFilter;
      const d = new Date(r.createdAt);
      const now = new Date();
      let matchesDate = true;
      if (dateFilter === '7d') {
        matchesDate = now.getTime() - d.getTime() <= 7 * 86400000;
      } else if (dateFilter === '30d') {
        matchesDate = now.getTime() - d.getTime() <= 30 * 86400000;
      } else if (dateFilter === 'today') {
        matchesDate = d.toDateString() === now.toDateString();
      }
      return matchesSearch && matchesStatus && matchesAsset && matchesDate;
    });
  }, [search, statusFilter, assetFilter, dateFilter]);

  const columns: Column<ProofRecord>[] = useMemo(
    () => [
      {
        key: 'id',
        header: 'Record ID',
        widthClass: 'min-w-[200px]',
        cell: (r) => (
          <code className="font-mono text-[12px] text-cyan-100/90">{shortId(r.id)}</code>
        ),
      },
      {
        key: 'asset',
        header: 'Asset',
        widthClass: 'w-[88px]',
        cell: (r) => <span className="font-medium text-slate-100">{r.asset}</span>,
      },
      {
        key: 'amount',
        header: 'Amount',
        widthClass: 'min-w-[120px]',
        cell: (r) => <span className="tabular-nums text-slate-200">{r.amount}</span>,
      },
      {
        key: 'source',
        header: 'Source',
        widthClass: 'min-w-[160px]',
        cell: (r) => <span className="text-slate-300">{r.sourceType}</span>,
      },
      {
        key: 'reference',
        header: 'Reference',
        widthClass: 'min-w-[180px]',
        cell: (r) => <span className="text-slate-400">{r.reference}</span>,
      },
      {
        key: 'status',
        header: 'Status',
        widthClass: 'w-[120px]',
        cell: (r) => <StatusBadge kind="status" value={r.status} />,
      },
      {
        key: 'anchor',
        header: 'Anchor',
        widthClass: 'w-[120px]',
        cell: (r) => <StatusBadge kind="anchor" value={r.anchorStatus} />,
      },
      {
        key: 'verification',
        header: 'Verification',
        widthClass: 'w-[120px]',
        cell: (r) => <StatusBadge kind="verification" value={r.verificationStatus} />,
      },
      {
        key: 'created',
        header: 'Created',
        widthClass: 'min-w-[160px]',
        cell: (r) => <span className="text-slate-500">{formatWhen(r.createdAt)}</span>,
      },
    ],
    [],
  );

  const inputClass =
    'h-10 w-full rounded-lg border border-white/10 bg-[var(--color-surface-2)] px-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30';

  return (
    <PageContainer>
      <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-50">Proof Records</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
            Institution-readable records for XRP and FXRP payment activity
          </p>
        </div>
        <ActionButton variant="primary" onClick={() => navigate('/records/create')}>
          Create Proof Record
        </ActionButton>
      </div>

      <FilterBar className="mb-6">
        <FilterField label="Search">
          <input
            className={inputClass}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Record ID, reference, or transaction hash"
          />
        </FilterField>
        <FilterField label="Status">
          <select
            className={inputClass}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="Pending">Pending</option>
            <option value="Processing">Processing</option>
            <option value="Complete">Complete</option>
            <option value="Failed">Failed</option>
            <option value="Anchored">Anchored</option>
            <option value="Verified">Verified</option>
          </select>
        </FilterField>
        <FilterField label="Asset">
          <select
            className={inputClass}
            value={assetFilter}
            onChange={(e) => setAssetFilter(e.target.value)}
          >
            <option value="all">All assets</option>
            <option value="XRP">XRP</option>
            <option value="FXRP">FXRP</option>
          </select>
        </FilterField>
        <FilterField label="Date">
          <select
            className={inputClass}
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="all">Any time</option>
            <option value="today">Today</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
        </FilterField>
      </FilterBar>

      {loading ? (
        <div className="space-y-3 rounded-xl border border-white/[0.08] bg-[var(--color-surface-2)]/40 p-6">
          <div className="h-4 w-1/3 animate-pulse rounded bg-slate-700/60" />
          <div className="h-10 w-full animate-pulse rounded bg-slate-800/60" />
          <div className="h-10 w-full animate-pulse rounded bg-slate-800/60" />
          <div className="h-10 w-full animate-pulse rounded bg-slate-800/60" />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={filtered}
          getRowKey={(r) => r.id}
          onRowClick={(r) => navigate(`/records/${encodeURIComponent(r.id)}`)}
          emptyMessage="No Proof Records match your filters. Adjust filters or create a new record."
        />
      )}
    </PageContainer>
  );
}
