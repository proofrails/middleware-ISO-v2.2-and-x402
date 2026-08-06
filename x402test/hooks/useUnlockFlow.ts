'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  useAccount,
  useBalance,
  useReadContract,
  useWriteContract,
  useSwitchChain,
  useConfig,
} from 'wagmi';
import { waitForTransactionReceipt, readContract } from 'wagmi/actions';
import { coston2 } from '@/lib/chains';
import {
  MOCK_USDT0_ADDRESS,
  FACILITATOR_ADDRESS,
  MINT_AMOUNT_RAW,
  MIN_GAS_BALANCE,
  PAYMENT_AMOUNT_RAW,
  mockUsdt0Abi,
  x402FacilitatorAbi,
  RESOURCE_ID,
} from '@/lib/contracts';
import { buildPaymentPayload, serializePayload } from '@/lib/x402';

export type FlowStep =
  | 'connect'
  | 'network'
  | 'gas'
  | 'token'
  | 'pay'
  | 'processing'
  | 'unlocked'
  | 'error';

export type ProcessingSubstep =
  | 'verifying'
  | 'settling'
  | 'confirming'
  | 'unlocking'
  | 'receipt';

export interface UnlockResult {
  settlement_tx_hash: string;
  payment_id: string;
  resource: {
    id: string;
    title: string;
    pdf_url: string;
    markdown_url: string;
    web_url: string;
  };
  receipt: {
    status: string;
    receipt_id: string | null;
    bundle_hash: string | null;
    verify_url: string | null;
  };
}

export function useUnlockFlow() {
  const config = useConfig();
  const { address, isConnected, chainId } = useAccount();
  const { switchChainAsync } = useSwitchChain();
  const { writeContractAsync } = useWriteContract();

  const [step, setStep] = useState<FlowStep>('connect');
  const [substep, setSubstep] = useState<ProcessingSubstep | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [result, setResult] = useState<UnlockResult | null>(null);

  // Native balance (C2FLR)
  const { data: gasBalance } = useBalance({
    address,
    chainId: coston2.id,
    query: { enabled: isConnected && chainId === coston2.id, refetchInterval: 5000 },
  });

  // MockUSDT0 balance
  const { data: tokenBalance, refetch: refetchTokenBalance } = useReadContract({
    address: MOCK_USDT0_ADDRESS,
    abi: mockUsdt0Abi,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    chainId: coston2.id,
    query: { enabled: !!address && chainId === coston2.id, refetchInterval: 5000 },
  });

  const hasGas = gasBalance ? gasBalance.value >= MIN_GAS_BALANCE : false;
  const hasToken = tokenBalance ? (tokenBalance as bigint) >= PAYMENT_AMOUNT_RAW : false;

  // Auto-advance step based on wallet state
  useEffect(() => {
    if (step === 'processing' || step === 'unlocked' || step === 'error') return;

    if (!isConnected) { setStep('connect'); return; }
    if (chainId !== coston2.id) { setStep('network'); return; }
    if (!hasGas) { setStep('gas'); return; }
    if (!hasToken) { setStep('token'); return; }
    setStep('pay');
  }, [isConnected, chainId, hasGas, hasToken, step]);

  const switchToCoston2 = useCallback(async () => {
    try {
      await switchChainAsync({ chainId: coston2.id });
    } catch (e) {
      setError((e as Error).message ?? 'Failed to switch network');
    }
  }, [switchChainAsync]);

  const mintToken = useCallback(async () => {
    if (!address) return;
    try {
      setError(null);
      const hash = await writeContractAsync({
        address: MOCK_USDT0_ADDRESS,
        abi: mockUsdt0Abi,
        functionName: 'mint',
        args: [address, MINT_AMOUNT_RAW],
        chainId: coston2.id,
      });
      await waitForTransactionReceipt(config, { hash, confirmations: 1 });
      await refetchTokenBalance();
    } catch (e) {
      setError((e as Error).message ?? 'Mint failed');
    }
  }, [address, writeContractAsync, config, refetchTokenBalance]);

  const pay = useCallback(async () => {
    if (!address) return;
    setError(null);
    setStep('processing');

    try {
      const payload = buildPaymentPayload(address);

      // 1. Precheck
      setSubstep('verifying');
      const [pId, valid] = await readContract(config, {
        address: FACILITATOR_ADDRESS,
        abi: x402FacilitatorAbi,
        functionName: 'verifyPayment',
        args: [payload],
        chainId: coston2.id,
      }) as [`0x${string}`, boolean];

      if (!valid) throw new Error('Payment payload rejected by facilitator precheck');

      // 2. Settle
      setSubstep('settling');
      const hash = await writeContractAsync({
        address: FACILITATOR_ADDRESS,
        abi: x402FacilitatorAbi,
        functionName: 'settlePayment',
        args: [payload],
        chainId: coston2.id,
      });
      setTxHash(hash);
      setPaymentId(pId);

      // 3. Confirm
      setSubstep('confirming');
      await waitForTransactionReceipt(config, { hash, confirmations: 1 });

      // 4. Backend unlock
      setSubstep('unlocking');
      const res = await fetch('/api/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: RESOURCE_ID,
          chain_id: 114,
          settlement_tx_hash: hash,
          payment_id: pId,
          from_address: address,
          payload: serializePayload(payload),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Unlock request failed' }));
        throw new Error((err as { error: string }).error ?? 'Unlock failed');
      }

      const data = await res.json() as UnlockResult;

      // 5. Show receipt step briefly
      setSubstep('receipt');
      setResult(data);

      setTimeout(() => {
        setStep('unlocked');
        setSubstep(null);
      }, 800);
    } catch (e) {
      console.error('[pay]', e);
      setError((e as Error).message ?? 'Payment failed');
      setStep('error');
      setSubstep(null);
    }
  }, [address, config, writeContractAsync]);

  const reset = useCallback(() => {
    setError(null);
    setTxHash(null);
    setPaymentId(null);
    setResult(null);
    setSubstep(null);
    setStep(isConnected ? (chainId === coston2.id ? 'pay' : 'network') : 'connect');
  }, [isConnected, chainId]);

  return {
    step,
    substep,
    error,
    txHash,
    paymentId,
    result,
    address,
    gasBalance,
    tokenBalance: tokenBalance as bigint | undefined,
    hasGas,
    hasToken,
    switchToCoston2,
    mintToken,
    pay,
    reset,
    refetchTokenBalance,
  };
}
