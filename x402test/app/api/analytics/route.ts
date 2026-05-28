import { NextRequest, NextResponse } from 'next/server';
import { trackEvent, AnalyticsEvent } from '@/lib/analytics';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const { event, properties } = await req.json();
    if (typeof event === 'string') {
      trackEvent(event as AnalyticsEvent, properties);
    }
  } catch {
    // silently ignore
  }
  return NextResponse.json({ ok: true });
}
