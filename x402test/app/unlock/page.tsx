'use client';

import { useUnlockFlow } from '@/hooks/useUnlockFlow';
import { StepIndicator, MobileStepBar } from '@/components/StepIndicator';
import { WalletConnectCard } from '@/components/WalletConnectCard';
import { NetworkGate } from '@/components/NetworkGate';
import { GasFaucetStep } from '@/components/GasFaucetStep';
import { MockUsdt0MintStep } from '@/components/MockUsdt0MintStep';
import { ResourcePreview } from '@/components/ResourcePreview';
import { PaymentSummary } from '@/components/PaymentSummary';
import { PaymentProgress } from '@/components/PaymentProgress';
import { UnlockSuccess } from '@/components/UnlockSuccess';
import { ReceiptCard } from '@/components/ReceiptCard';
import { VerificationBridge } from '@/components/VerificationBridge';
import { ErrorRecovery } from '@/components/ErrorRecovery';

export default function UnlockPage() {
  const flow = useUnlockFlow();

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-100">Unlock the research brief</h1>
        <p className="text-slate-400 text-sm mt-1">
          Complete the Coston2 testnet flow to access the Flare x ProofRails thesis.
        </p>
      </div>

      <div className="flex gap-10">
        <StepIndicator current={flow.step} />

        <div className="flex-1 min-w-0 space-y-5">
          <MobileStepBar current={flow.step} />

          {flow.step === 'connect' && <WalletConnectCard />}

          {flow.step === 'network' && (
            <NetworkGate onSwitch={flow.switchToCoston2} />
          )}

          {flow.step === 'gas' && (
            <GasFaucetStep hasGas={flow.hasGas} />
          )}

          {flow.step === 'token' && (
            <MockUsdt0MintStep
              tokenBalance={flow.tokenBalance}
              onMint={flow.mintToken}
            />
          )}

          {flow.step === 'pay' && (
            <>
              <ResourcePreview />
              <PaymentSummary
                address={flow.address ?? ''}
                onPay={flow.pay}
              />
            </>
          )}

          {flow.step === 'processing' && (
            <PaymentProgress substep={flow.substep} txHash={flow.txHash} />
          )}

          {flow.step === 'unlocked' && flow.result && (
            <>
              <UnlockSuccess result={flow.result} txHash={flow.txHash} />
              <ReceiptCard
                paymentId={flow.paymentId}
                initialReceipt={flow.result.receipt}
              />
              <VerificationBridge
                paymentId={flow.paymentId}
                verifyUrl={flow.result.receipt.verify_url}
                receiptId={flow.result.receipt.receipt_id}
                bundleHash={flow.result.receipt.bundle_hash}
              />
            </>
          )}

          {flow.step === 'error' && (
            <ErrorRecovery
              error={flow.error ?? 'An unknown error occurred'}
              txHash={flow.txHash}
              onRetry={flow.reset}
            />
          )}

          {/* Always show wallet status when not in processing/unlocked/error */}
          {!['processing', 'unlocked', 'error'].includes(flow.step) && flow.address && (
            <div className="card-sm flex items-center justify-between text-xs text-slate-500">
              <span>Connected: <span className="font-mono text-slate-400">{flow.address.slice(0, 8)}…{flow.address.slice(-6)}</span></span>
              {flow.gasBalance && (
                <span>
                  {Number(flow.gasBalance.formatted).toFixed(3)} C2FLR
                  {' · '}
                  {flow.tokenBalance !== undefined
                    ? `${(Number(flow.tokenBalance) / 1e6).toFixed(3)} MockUSDT0`
                    : ''}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
