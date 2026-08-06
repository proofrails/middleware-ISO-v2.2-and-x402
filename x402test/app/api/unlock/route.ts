import { NextRequest, NextResponse } from 'next/server';
import { createPublicClient, http, getAddress } from 'viem';
import { coston2 } from '@/lib/chains';
import {
  FACILITATOR_ADDRESS,
  MOCK_USDT0_ADDRESS,
  RECIPIENT_ADDRESS,
  RESOURCE_ID,
  RESOURCE_TITLE,
  MIN_AMOUNT_RAW,
  x402FacilitatorAbi,
} from '@/lib/contracts';
import { findByPaymentId, createUnlock } from '@/lib/unlocks';
import { createResourceToken } from '@/lib/token';
import { createProofRailsReceipt } from '@/lib/proofrails';
import { trackEvent } from '@/lib/analytics';

const client = createPublicClient({
  chain: coston2,
  transport: http(),
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as {
      resource_id?: string;
      settlement_tx_hash: string;
      payment_id: string;
      from_address: string;
      chain_id: number;
    };

    const { settlement_tx_hash, payment_id, from_address, chain_id } = body;

    if (!settlement_tx_hash || !payment_id || !from_address) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }
    if (chain_id !== 114) {
      return NextResponse.json({ error: 'Wrong chain — Coston2 (114) required' }, { status: 400 });
    }

    let payerAddress: `0x${string}`;
    try {
      payerAddress = getAddress(from_address);
    } catch {
      return NextResponse.json({ error: 'Invalid from_address' }, { status: 400 });
    }

    const resourceId = body.resource_id ?? RESOURCE_ID;

    // Idempotent: already unlocked for this payment_id
    const existing = findByPaymentId(payment_id);
    if (existing) {
      const token = createResourceToken(payment_id);
      return NextResponse.json({
        status: 'unlocked',
        resource: buildResource(resourceId, token),
        payment: { network: 'flare-coston2', chain_id: 114, settlement_tx_hash, payment_id },
        receipt: {
          status: existing.receipt_id ? 'created' : 'pending_creation',
          receipt_id: existing.receipt_id,
          bundle_hash: existing.bundle_hash,
          verify_url: existing.verify_url,
        },
        idempotent: true,
      });
    }

    // 1. Verify tx exists and succeeded
    let txReceipt;
    try {
      txReceipt = await client.getTransactionReceipt({
        hash: settlement_tx_hash as `0x${string}`,
      });
    } catch {
      return NextResponse.json({ error: 'Transaction not found on Coston2' }, { status: 422 });
    }

    if (txReceipt.status !== 'success') {
      return NextResponse.json({ error: 'Transaction reverted or failed' }, { status: 422 });
    }

    // 2. Verify tx target is the facilitator
    if (txReceipt.to?.toLowerCase() !== FACILITATOR_ADDRESS.toLowerCase()) {
      return NextResponse.json({ error: 'Transaction target is not the x402 facilitator' }, { status: 422 });
    }

    // 3. Read payment record from facilitator
    let payment: { from: string; to: string; token: string; amount: bigint; settled: boolean };
    try {
      payment = await client.readContract({
        address: FACILITATOR_ADDRESS,
        abi: x402FacilitatorAbi,
        functionName: 'getPayment',
        args: [payment_id as `0x${string}`],
      }) as { from: string; to: string; token: string; amount: bigint; nonce: string; timestamp: bigint; settled: boolean };
    } catch {
      return NextResponse.json({ error: 'Could not read payment record from facilitator' }, { status: 422 });
    }

    if (!payment.settled) {
      return NextResponse.json({ error: 'Payment not settled in facilitator' }, { status: 422 });
    }
    if (payment.from.toLowerCase() !== payerAddress.toLowerCase()) {
      return NextResponse.json({ error: 'Payer address mismatch' }, { status: 422 });
    }
    if (payment.to.toLowerCase() !== RECIPIENT_ADDRESS.toLowerCase()) {
      return NextResponse.json({ error: 'Recipient mismatch' }, { status: 422 });
    }
    if (payment.token.toLowerCase() !== MOCK_USDT0_ADDRESS.toLowerCase()) {
      return NextResponse.json({ error: 'Token mismatch — MockUSDT0 required' }, { status: 422 });
    }
    if (payment.amount < MIN_AMOUNT_RAW) {
      return NextResponse.json({ error: 'Insufficient payment amount' }, { status: 422 });
    }

    // 4. Store unlock record
    const record = createUnlock({
      resource_id: resourceId,
      wallet_address: payerAddress,
      chain_id: 114,
      payment_id,
      settlement_tx_hash,
      token: MOCK_USDT0_ADDRESS,
      amount_raw: payment.amount.toString(),
      recipient: RECIPIENT_ADDRESS,
    });

    trackEvent('unlock_success', { resource_id: resourceId, chain_id: 114 });

    // 5. Async receipt creation — does not block unlock
    createProofRailsReceipt({
      unlockId: record.id,
      settlementTxHash: settlement_tx_hash,
      paymentId: payment_id,
      payerAddress: payerAddress.toLowerCase(),
      amount: payment.amount.toString(),
    }).catch(console.error);

    const token = createResourceToken(payment_id);

    return NextResponse.json({
      status: 'unlocked',
      resource: buildResource(resourceId, token),
      payment: {
        network: 'flare-coston2',
        chain_id: 114,
        token: 'MockUSDT0',
        amount: '0.001',
        settlement_tx_hash,
        payment_id,
      },
      receipt: {
        status: 'pending_creation',
        receipt_id: null,
        bundle_hash: null,
        verify_url: null,
      },
    });
  } catch (err) {
    console.error('[unlock] error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

function buildResource(resourceId: string, token: string) {
  return {
    id: resourceId,
    title: RESOURCE_TITLE,
    pdf_url: `/api/resource/flare-proofrails-thesis-v1.pdf?token=${token}`,
    markdown_url: `/api/resource/flare-proofrails-thesis-v1.md?token=${token}`,
    web_url: `/read/${resourceId}?token=${token}`,
  };
}
