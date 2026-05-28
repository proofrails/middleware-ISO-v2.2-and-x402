import { updateReceipt } from './unlocks';

interface ReceiptInput {
  unlockId: string;
  settlementTxHash: string;
  paymentId: string;
  payerAddress: string;
  amount: string;
}

interface ReceiptResponse {
  receipt_id?: string;
  bundle_hash?: string;
  verify_url?: string;
}

export async function createProofRailsReceipt(input: ReceiptInput): Promise<void> {
  const apiBase = process.env.PROOFRAILS_API_BASE ?? 'https://app.proofrails.com';
  const apiKey = process.env.PROOFRAILS_API_KEY;

  if (!apiKey) {
    console.warn('[proofrails] PROOFRAILS_API_KEY not set — skipping receipt creation');
    return;
  }

  try {
    const res = await fetch(`${apiBase}/v1/iso/record-tip`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        tip_tx_hash: input.settlementTxHash,
        chain: 'flare-coston2',
        amount: '0.001',
        currency: 'MockUSDT0',
        sender_wallet: input.payerAddress,
        receiver_wallet: '0x0A617D605a1010a74B8dA756E48D75bCef110ef4',
        reference: `proofrails:x402test:flare-proofrails-thesis-v1:${input.paymentId}`,
      }),
    });

    if (!res.ok) {
      console.warn(`[proofrails] receipt creation returned ${res.status}`);
      return;
    }

    const data = (await res.json()) as ReceiptResponse;
    if (data.receipt_id || data.bundle_hash) {
      await updateReceipt(input.paymentId, {
        receipt_id: data.receipt_id,
        bundle_hash: data.bundle_hash,
        verify_url: data.verify_url ?? (data.bundle_hash
          ? `${apiBase}/verify?bundle_hash=${data.bundle_hash}`
          : undefined),
      });
    }
  } catch (err) {
    console.error('[proofrails] receipt creation error:', err);
  }
}
