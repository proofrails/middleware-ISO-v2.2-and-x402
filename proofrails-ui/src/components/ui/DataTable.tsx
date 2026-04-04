import type { ReactNode } from 'react';

export type Column<T> = {
  key: string;
  header: string;
  widthClass?: string;
  cell: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  getRowKey: (row: T) => string;
};

export function DataTable<T>({
  columns,
  rows,
  onRowClick,
  emptyMessage = 'No records match the current filters.',
  getRowKey,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 bg-[var(--color-surface-1)]/50 px-6 py-16 text-center">
        <p className="text-sm text-slate-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.08] bg-[var(--color-surface-2)]/60 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-white/[0.08] bg-[var(--color-surface-1)]/80">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 ${c.widthClass ?? ''}`}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={getRowKey(row)}
                onClick={() => onRowClick?.(row)}
                onKeyDown={(e) => {
                  if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onRowClick(row);
                  }
                }}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? 'button' : undefined}
                className={`border-b border-white/[0.05] transition-colors last:border-0 ${
                  onRowClick
                    ? 'cursor-pointer hover:bg-cyan-500/[0.04] focus-visible:bg-cyan-500/[0.06] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-cyan-500/40'
                    : ''
                }`}
              >
                {columns.map((c) => (
                  <td key={c.key} className={`px-4 py-3 text-slate-200 ${c.widthClass ?? ''}`}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
