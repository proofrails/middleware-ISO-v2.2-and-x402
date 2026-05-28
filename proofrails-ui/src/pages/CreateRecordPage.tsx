import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import { PageContainer } from '../components/layout/PageContainer';
import { ActionButton } from '../components/ui/ActionButton';
import { Card } from '../components/ui/Card';
import type { SourceType } from '../types/record';

const inputClass =
  'mt-1 w-full rounded-lg border border-white/10 bg-[var(--color-surface-1)] px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/30';
const labelClass = 'text-xs font-medium uppercase tracking-wider text-slate-500';

export function CreateRecordPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [sourceType, setSourceType] = useState<SourceType>('XRPL payment');
  const [txHash, setTxHash] = useState('');
  const [asset, setAsset] = useState('XRP');
  const [amount, setAmount] = useState('');
  const [sender, setSender] = useState('');
  const [receiver, setReceiver] = useState('');
  const [reference, setReference] = useState('');
  const [counterparty, setCounterparty] = useState('');
  const [purpose, setPurpose] = useState('');
  const [invoiceId, setInvoiceId] = useState('');
  const [category, setCategory] = useState('');
  const [notes, setNotes] = useState('');
  const [parsing, setParsing] = useState(false);
  const [generating, setGenerating] = useState(false);

  const handleParse = () => {
    setParsing(true);
    window.setTimeout(() => {
      setAsset(sourceType.includes('FXRP') ? 'FXRP' : 'XRP');
      setAmount('12,450.00');
      setSender(
        sourceType === 'FXRP payment'
          ? '0x71bE63f3384f5fb989958a376552a5b48a633cD2'
          : 'rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe',
      );
      setReceiver(
        sourceType === 'FXRP payment'
          ? '0xFABB0ac9d68Ba0f1A0e1C2Ef3e4D5A6B7C8D9E0F'
          : 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh',
      );
      setReference('INV-2026-DRAFT-8840');
      setParsing(false);
    }, 900);
  };

  const handleGenerate = () => {
    setGenerating(true);
    window.setTimeout(() => {
      setGenerating(false);
      showToast('Proof Record draft created and queued for evidence generation.');
      navigate('/records');
    }, 1100);
  };

  return (
    <PageContainer>
      <div className="mb-8">
        <h2 className="text-2xl font-semibold tracking-tight text-slate-50">Create Proof Record</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Capture a payment event and attach business context. ProofRails will normalize the event,
          generate evidence, and queue Flare anchoring.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h3 className="text-base font-semibold text-slate-100">Source Payment Event</h3>
          <p className="mt-1 text-sm text-slate-500">
            Identify the on-ledger or programmable event to anchor as a Proof Record.
          </p>
          <div className="mt-6 space-y-4">
            <div>
              <label className={labelClass} htmlFor="sourceType">
                Source type
              </label>
              <select
                id="sourceType"
                className={inputClass}
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as SourceType)}
              >
                <option value="XRPL payment">XRPL payment</option>
                <option value="FXRP payment">FXRP payment</option>
                <option value="Programmable payment event">Programmable payment event</option>
              </select>
            </div>
            <div>
              <label className={labelClass} htmlFor="txHash">
                Transaction hash / event ID
              </label>
              <input
                id="txHash"
                className={`${inputClass} font-mono text-[13px]`}
                value={txHash}
                onChange={(e) => setTxHash(e.target.value)}
                placeholder="Paste XRPL tx hash, EVM tx hash, or internal event ID"
              />
              <p className="mt-1.5 text-xs text-slate-600">
                Hashes are validated against the selected source environment before ingest.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelClass} htmlFor="asset">
                  Asset
                </label>
                <select
                  id="asset"
                  className={inputClass}
                  value={asset}
                  onChange={(e) => setAsset(e.target.value)}
                >
                  <option value="XRP">XRP</option>
                  <option value="FXRP">FXRP</option>
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="amount">
                  Amount
                </label>
                <input
                  id="amount"
                  className={`${inputClass} tabular-nums`}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                />
              </div>
            </div>
            <div>
              <label className={labelClass} htmlFor="sender">
                Sender
              </label>
              <input
                id="sender"
                className={`${inputClass} font-mono text-[12px]`}
                value={sender}
                onChange={(e) => setSender(e.target.value)}
                placeholder="r-address or 0x…"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="receiver">
                Receiver
              </label>
              <input
                id="receiver"
                className={`${inputClass} font-mono text-[12px]`}
                value={receiver}
                onChange={(e) => setReceiver(e.target.value)}
                placeholder="r-address or 0x…"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="reference">
                Reference
              </label>
              <input
                id="reference"
                className={inputClass}
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Invoice, settlement, or payout reference"
              />
            </div>
            <ActionButton
              variant="secondary"
              className="w-full sm:w-auto"
              disabled={parsing}
              onClick={handleParse}
            >
              {parsing ? 'Parsing event…' : 'Parse Event'}
            </ActionButton>
          </div>
        </Card>

        <Card>
          <h3 className="text-base font-semibold text-slate-100">Business Context</h3>
          <p className="mt-1 text-sm text-slate-500">
            Optional metadata improves audit trails and export packages for counterparties.
          </p>
          <div className="mt-6 space-y-4">
            <div>
              <label className={labelClass} htmlFor="counterparty">
                Counterparty name
              </label>
              <input
                id="counterparty"
                className={inputClass}
                value={counterparty}
                onChange={(e) => setCounterparty(e.target.value)}
                placeholder="Legal entity or desk name"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="purpose">
                Payment purpose
              </label>
              <input
                id="purpose"
                className={inputClass}
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Trade settlement, coupon, liquidity move"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="invoiceId">
                Invoice / order ID
              </label>
              <input
                id="invoiceId"
                className={inputClass}
                value={invoiceId}
                onChange={(e) => setInvoiceId(e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="category">
                Category / tag
              </label>
              <input
                id="category"
                className={inputClass}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="Treasury, AP, settlement…"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="notes">
                Notes
              </label>
              <textarea
                id="notes"
                className={`${inputClass} min-h-[120px] resize-y`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Internal notes — excluded from external evidence bundles by default."
              />
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-8 flex flex-col gap-3 border-t border-white/[0.08] pt-6 sm:flex-row sm:justify-end">
        <ActionButton variant="secondary" onClick={() => navigate('/records')}>
          Cancel
        </ActionButton>
        <ActionButton variant="primary" disabled={generating} onClick={handleGenerate}>
          {generating ? 'Generating Proof Record…' : 'Generate Proof Record'}
        </ActionButton>
      </div>
    </PageContainer>
  );
}
