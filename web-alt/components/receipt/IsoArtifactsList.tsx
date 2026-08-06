import type { ISOArtifact } from "../../lib/proofrails";
import { shortHash } from "../../lib/proofrails";

export default function IsoArtifactsList({ artifacts }: { artifacts: ISOArtifact[] }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-black tracking-tight">ISO-style artifacts</h2>
      <p className="mt-2 text-sm text-slate-600">These records translate the onchain payment into finance-readable evidence. They are ISO-style artifacts, not a claim of bank-network acceptance.</p>
      <div className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200">
        {artifacts.length === 0 ? <div className="p-4 text-sm text-slate-500">Artifacts are not available yet.</div> : artifacts.map((item) => (
          <div key={`${item.type}-${item.url}`} className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div><div className="font-bold">{item.type}</div><div className="font-mono text-xs text-slate-500">sha256: {shortHash(item.sha256)}</div></div>
            <a href={item.url} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">Open XML</a>
          </div>
        ))}
      </div>
    </section>
  );
}
