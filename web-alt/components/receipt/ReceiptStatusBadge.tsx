import type { ReceiptStatus } from "../../lib/proofrails";

const labels: Record<ReceiptStatus, string> = {
  pending: "Preparing evidence",
  processing: "Processing",
  awaiting_anchor: "Awaiting anchor",
  anchored: "Verified receipt",
  failed: "Needs attention",
};

const styles: Record<ReceiptStatus, string> = {
  pending: "border-slate-200 bg-slate-100 text-slate-700",
  processing: "border-blue-200 bg-blue-50 text-blue-800",
  awaiting_anchor: "border-amber-200 bg-amber-50 text-amber-800",
  anchored: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-red-200 bg-red-50 text-red-800",
};

export default function ReceiptStatusBadge({ status }: { status: ReceiptStatus }) {
  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${styles[status] || styles.pending}`}>{labels[status] || status}</span>;
}
