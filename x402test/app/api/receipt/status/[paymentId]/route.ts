import { NextRequest, NextResponse } from 'next/server';
import { findByPaymentId } from '@/lib/unlocks';

export async function GET(
  _req: NextRequest,
  { params }: { params: { paymentId: string } },
) {
  const record = findByPaymentId(params.paymentId);
  if (!record) {
    return NextResponse.json({ error: 'Payment record not found' }, { status: 404 });
  }

  return NextResponse.json({
    payment_id: record.payment_id,
    status: record.status,
    receipt: {
      status: record.receipt_id ? 'created' : 'pending',
      receipt_id: record.receipt_id,
      bundle_hash: record.bundle_hash,
      verify_url: record.verify_url,
    },
    created_at: record.created_at,
  });
}
