import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { Card } from '../components/ui/Card';
import { SectionHeader } from '../components/ui/SectionHeader';

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="flex gap-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 font-mono text-sm font-semibold text-cyan-200">
        {n}
      </span>
      <div>
        <p className="font-medium text-slate-100">{title}</p>
        <div className="mt-1 text-sm leading-relaxed text-slate-400">{children}</div>
      </div>
    </li>
  );
}

export function DocsPage() {
  return (
    <PageContainer>
      <div className="mx-auto max-w-3xl">
        <p className="text-sm text-slate-500">
          How to operate ProofRails in your workspace — from capture to verification and export.
        </p>
      </div>

      <div className="mx-auto mt-8 max-w-3xl space-y-8">
        <Card>
          <SectionHeader
            title="What ProofRails is"
            description="A records and evidence layer for XRP and FXRP payment activity — not a wallet, exchange, or trading product."
          />
          <p className="text-sm leading-relaxed text-slate-300">
            ProofRails turns digital payment events into <strong className="font-medium text-slate-100">Proof Records</strong>: operational objects you can review, anchor on Flare, verify against on-chain commitments, and export as evidence bundles (including ISO-aligned artifacts). The console is built for treasury, operations, and compliance workflows around tokenized payment rails.
          </p>
        </Card>

        <Card>
          <SectionHeader
            title="What you are supposed to do"
            description="Your job in the console is to govern the lifecycle of Proof Records for your organization."
          />
          <ul className="list-inside list-disc space-y-2 text-sm text-slate-300">
            <li>
              <span className="text-slate-100">Capture</span> payment events (XRPL, FXRP, or programmable) and attach business context so every record is institution-readable.
            </li>
            <li>
              <span className="text-slate-100">Monitor</span> processing, anchoring, and verification status until each record reaches a clear terminal state for audit.
            </li>
            <li>
              <span className="text-slate-100">Verify</span> independently that an evidence bundle matches its Flare anchor when auditors, counterparties, or internal control ask for proof.
            </li>
            <li>
              <span className="text-slate-100">Export</span> ISO, JSON, PDF, and sealed bundles according to your workspace defaults and counterparty requirements.
            </li>
          </ul>
        </Card>

        <Card>
          <SectionHeader
            title="What you can do in this application"
            description="Capabilities available from the navigation and record workflows."
          />
          <div className="overflow-hidden rounded-lg border border-white/[0.06]">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/[0.08] bg-[var(--color-surface-1)]/80">
                  <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Area
                  </th>
                  <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                <tr className="border-b border-white/[0.05]">
                  <td className="px-4 py-3 font-medium text-slate-200">Records</td>
                  <td className="px-4 py-3">
                    Search and filter Proof Records; open detail; start{' '}
                    <Link className="text-cyan-400 hover:text-cyan-300" to="/records/create">
                      Create Proof Record
                    </Link>
                    .
                  </td>
                </tr>
                <tr className="border-b border-white/[0.05]">
                  <td className="px-4 py-3 font-medium text-slate-200">Proof Record detail</td>
                  <td className="px-4 py-3">
                    Review payment summary, evidence, Flare anchor, and artifacts; run Verify; export bundle, ISO, or JSON; open explorer for anchor tx when present.
                  </td>
                </tr>
                <tr className="border-b border-white/[0.05]">
                  <td className="px-4 py-3 font-medium text-slate-200">Verify</td>
                  <td className="px-4 py-3">
                    Submit a Proof Record ID or evidence bundle hash (optional bundle URL) and run an independent verification pass against Flare.
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-medium text-slate-200">Settings</td>
                  <td className="px-4 py-3">
                    Configure project identity, API keys for automation, Flare anchoring target, and default export behavior.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="End-to-end workflow"
            description="Typical path from event to verified, exportable evidence."
          />
          <ol className="space-y-5">
            <Step n={1} title="Ingest the source event">
              On{' '}
              <Link className="text-cyan-400 hover:text-cyan-300" to="/records/create">
                Create Proof Record
              </Link>
              , choose the <span className="text-slate-200">source type</span> (XRPL payment, FXRP payment, or programmable payment event), paste the{' '}
              <span className="text-slate-200">transaction hash or event ID</span>, then use{' '}
              <span className="text-slate-200">Parse Event</span> to normalize fields. Adjust asset, amount, sender, receiver, and reference if your policy requires manual confirmation.
            </Step>
            <Step n={2} title="Attach business context">
              Complete <span className="text-slate-200">Business Context</span>: counterparty, purpose, invoice/order ID, category, and internal notes. This metadata flows into exports and audit narratives — keep it aligned with how your institution names settlements and payouts.
            </Step>
            <Step n={3} title="Generate the Proof Record">
              Click <span className="text-slate-200">Generate Proof Record</span>. The system creates the operational record, builds the evidence bundle, and queues Flare anchoring per workspace rules. You will return to the list when processing completes in this prototype.
            </Step>
            <Step n={4} title="Track status on Records">
              On{' '}
              <Link className="text-cyan-400 hover:text-cyan-300" to="/records">
                Proof Records
              </Link>
              , use search (ID, reference, hash) and filters (status, asset, date). Open any row to inspect the full timeline: ingest → bundle → anchor → verification.
            </Step>
            <Step n={5} title="Confirm anchor and evidence">
              On the detail page, review <span className="text-slate-200">Evidence and Verification</span> and <span className="text-slate-200">Flare Anchor</span>. If anchoring failed, use <span className="text-slate-200">Retry anchor</span> after resolving the underlying issue (e.g. registry or gas boundary — see your runbook).
            </Step>
            <Step n={6} title="Verify and export">
              Use <span className="text-slate-200">Verify</span> on the record or visit{' '}
              <Link className="text-cyan-400 hover:text-cyan-300" to="/verify">
                Verify
              </Link>{' '}
              with an ID or bundle hash. When satisfied, use <span className="text-slate-200">Export Bundle</span>, <span className="text-slate-200">Export ISO</span>, or <span className="text-slate-200">Export JSON</span>; use <span className="text-slate-200">Artifacts</span> for per-format view, download, or signed links.
            </Step>
          </ol>
        </Card>

        <Card>
          <SectionHeader
            title="Proof Records list — in detail"
            description="The main operational dashboard."
          />
          <ul className="space-y-3 text-sm text-slate-300">
            <li>
              <span className="font-medium text-slate-200">Search</span> matches Record ID, reference text, and source transaction hash — use it when operations paste an ID from email or a ticket.
            </li>
            <li>
              <span className="font-medium text-slate-200">Status</span> reflects the overall Proof Record lifecycle (e.g. Pending, Processing, Complete, Anchored, Verified, Failed). Align internal SLAs to these states.
            </li>
            <li>
              <span className="font-medium text-slate-200">Anchor</span> and <span className="font-medium text-slate-200">Verification</span> columns are shown separately so you can see “bundle ready” vs “on-chain committed” vs “independently checked.”
            </li>
            <li>
              Click a <span className="font-medium text-slate-200">row</span> to open <span className="text-slate-200">Proof Record Details</span>; keyboard focus is supported for accessibility.
            </li>
          </ul>
        </Card>

        <Card>
          <SectionHeader
            title="Create Proof Record — field guide"
            description="Source card vs. business card — what each field is for."
          />
          <div className="space-y-4 text-sm text-slate-300">
            <div>
              <p className="font-medium text-slate-200">Source Payment Event</p>
              <p className="mt-1 leading-relaxed text-slate-400">
                <span className="text-slate-300">Source type</span> selects which parser and environment rules apply. <span className="text-slate-300">Transaction hash / event ID</span> is the authoritative link to the ledger or event bus. <span className="text-slate-300">Parse Event</span> (demo) simulates server-side normalization — in production, invalid hashes are rejected before a record is created.
              </p>
            </div>
            <div>
              <p className="font-medium text-slate-200">Business Context</p>
              <p className="mt-1 leading-relaxed text-slate-400">
                Optional for ingestion but <span className="text-slate-300">strongly recommended</span> for anything that will be shown to compliance or external parties. <span className="text-slate-300">Notes</span> may be excluded from external PDFs depending on{' '}
                <Link className="text-cyan-400 hover:text-cyan-300" to="/settings">
                  Settings → Export defaults
                </Link>
                .
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Verify page — in detail"
            description="When to use standalone verification instead of the button on a record."
          />
          <p className="text-sm leading-relaxed text-slate-300">
            Use the dedicated{' '}
            <Link className="text-cyan-400 hover:text-cyan-300" to="/verify">
              Verify
            </Link>{' '}
            flow when you received a <span className="text-slate-200">bundle hash</span> or <span className="text-slate-200">Proof Record ID</span> out of band (e.g. counterparty email, auditor request) and need a clean verification result without navigating the full list. Enter an optional <span className="text-slate-200">bundle URL</span> if the package was delivered separately from the console. <span className="text-slate-200">Run Verification</span> compares the bundle digest to the Flare anchor and surfaces technical notes for your operations log.
          </p>
        </Card>

        <Card>
          <SectionHeader
            title="Settings — in detail"
            description="Workspace-scoped configuration."
          />
          <ul className="space-y-2 text-sm text-slate-300">
            <li>
              <span className="font-medium text-slate-200">Project info</span> — name and environment label appear on exports and audit trails.
            </li>
            <li>
              <span className="font-medium text-slate-200">API keys</span> — for programmatic ingest and verification; rotate on your security schedule.
            </li>
            <li>
              <span className="font-medium text-slate-200">Flare anchoring</span> — network (e.g. test vs mainnet) and registry contract identity for commitments.
            </li>
            <li>
              <span className="font-medium text-slate-200">Export defaults</span> — whether ISO artifacts and signing are included by default, and redaction of internal notes from PDF summaries.
            </li>
          </ul>
        </Card>

        <Card>
          <SectionHeader
            title="About this prototype"
            description="What is simulated vs. what a production deployment would add."
          />
          <p className="text-sm leading-relaxed text-slate-400">
            This UI is a <span className="text-slate-300">frontend prototype</span> with mock data and simulated delays. There is no live XRPL/Flare connection in the browser: parsing, anchoring, and verification toasts represent intended operator feedback only. Connect a real backend and signing infrastructure before using in production compliance contexts.
          </p>
          <p className="mt-4 text-sm text-slate-500">
            For setup and scripts, see the project <span className="text-slate-400">README.md</span> in the <span className="font-mono text-xs text-cyan-200/80">proofrails-ui</span> folder.
          </p>
        </Card>
      </div>
    </PageContainer>
  );
}
