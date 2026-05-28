import { PageContainer } from '../components/layout/PageContainer';
import { ActionButton } from '../components/ui/ActionButton';
import { Card } from '../components/ui/Card';
import { SectionHeader } from '../components/ui/SectionHeader';
import { useToast } from '../context/ToastContext';

const inputClass =
  'mt-1 w-full rounded-lg border border-white/10 bg-[var(--color-surface-1)] px-3 py-2 text-sm text-slate-200 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30';

export function SettingsPage() {
  const { showToast } = useToast();

  return (
    <PageContainer>
      <div className="mx-auto max-w-3xl space-y-6">
        <Card>
          <SectionHeader
            title="Project info"
            description="Workspace identity used in exports and audit trails."
          />
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Project name
              </label>
              <input className={inputClass} defaultValue="Acme Treasury Ops" />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Environment
              </label>
              <select className={inputClass} defaultValue="production">
                <option value="production">Production</option>
                <option value="staging">Staging</option>
              </select>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="API key management"
            description="Server-to-server access for ingest and verification automation."
            action={
              <ActionButton variant="secondary" onClick={() => showToast('New API key created (demo).')}>
                Rotate key
              </ActionButton>
            }
          />
          <div className="space-y-3">
            <div className="rounded-lg border border-white/[0.08] bg-[var(--color-surface-1)]/80 px-3 py-2 font-mono text-xs text-cyan-100/80">
              pr_live_••••••••••••••••8f3c
            </div>
            <p className="text-xs text-slate-600">
              Keys are scoped to this workspace. Last rotated 14 days ago.
            </p>
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Flare anchoring configuration"
            description="Network and registry targets for evidence commitments."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Network
              </label>
              <select className={inputClass} defaultValue="coston2">
                <option value="coston2">Coston2 (test)</option>
                <option value="flare">Flare Mainnet</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Registry contract
              </label>
              <input
                className={`${inputClass} font-mono text-[11px]`}
                defaultValue="0xEvidenceAnchorRegistry…"
                readOnly
              />
            </div>
          </div>
          <ActionButton
            variant="secondary"
            className="mt-4"
            onClick={() => showToast('Anchoring settings saved.')}
          >
            Save changes
          </ActionButton>
        </Card>

        <Card>
          <SectionHeader
            title="Export defaults"
            description="Default bundles for ISO, JSON, and PDF outputs."
          />
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" defaultChecked className="rounded border-white/20 bg-slate-800" />
              Include ISO 20022 artifacts in evidence bundle
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" defaultChecked className="rounded border-white/20 bg-slate-800" />
              Sign exports with workspace HSM key
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" className="rounded border-white/20 bg-slate-800" />
              Redact internal notes from PDF summary
            </label>
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}
