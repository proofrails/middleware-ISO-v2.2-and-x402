import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/db';
import { trackEvent } from '@/lib/analytics';
import { randomUUID } from 'crypto';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as {
      message: string;
      wallet_address?: string;
      payment_id?: string;
      rating?: number;
    };

    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json({ error: 'message is required' }, { status: 400 });
    }
    if (body.message.length > 2000) {
      return NextResponse.json({ error: 'message too long' }, { status: 400 });
    }

    const db = getDb();
    db.prepare(`
      INSERT INTO feedback (id, wallet_address, payment_id, message, rating)
      VALUES (?, ?, ?, ?, ?)
    `).run(
      randomUUID(),
      body.wallet_address ?? null,
      body.payment_id ?? null,
      body.message,
      body.rating ?? null,
    );

    trackEvent('feedback_submitted');
    return NextResponse.json({ status: 'received' });
  } catch (err) {
    console.error('[feedback]', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
