import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { ReceiptStatus } from "../../lib/proofrails";

const steps = [
  { key: "pending", label: "Receipt created", body: "ProofRails accepted the payment reference." },
  { key: "processing", label: "ISO-style artifacts", body: "Finance-readable records are generated." },
  { key: "awaiting_anchor", label: "Evidence bundle", body: "The receipt, XML, manifest, and checksums are packaged." },
  { key: "anchored", label: "Onchain anchor", body: "The bundle hash is committed onchain and ready to verify." },
] as const;

function rank(status: ReceiptStatus) {
  if (status === "pending") return 0;
  if (status === "processing") return 1;
  if (status === "awaiting_anchor") return 2;
  if (status === "anchored") return 3;
  return -1;
}

export default function ReceiptTimeline({ status }: { status: ReceiptStatus }) {
  const current = rank(status);
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {steps.map((step, idx) => {
        const done = current >= idx;
        const active = current === idx && status !== "anchored";
        const failed = status === "failed" && idx === 0;
        return (
          <div key={step.key} className={`rounded-2xl border p-4 ${done ? "border-slate-900 bg-slate-950 text-white" : "border-slate-200 bg-white"}`}>
            <div className="mb-3 flex items-center gap-2">
              {failed ? <XCircle className="h-5 w-5 text-red-500" /> : active ? <Loader2 className="h-5 w-5 animate-spin" /> : done ? <CheckCircle2 className="h-5 w-5 text-emerald-400" /> : <Circle className="h-5 w-5 text-slate-300" />}
              <div className="text-sm font-semibold">{step.label}</div>
            </div>
            <p className={`text-sm ${done ? "text-slate-300" : "text-slate-600"}`}>{step.body}</p>
          </div>
        );
      })}
    </div>
  );
}
