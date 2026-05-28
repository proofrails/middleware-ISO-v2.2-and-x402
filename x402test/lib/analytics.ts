import { getDb } from './db';
import { randomUUID } from 'crypto';

export type AnalyticsEvent =
  | 'page_view'
  | 'wallet_connect_started'
  | 'wallet_connected'
  | 'network_switch_started'
  | 'network_switch_success'
  | 'faucet_opened'
  | 'gas_detected'
  | 'mock_usdt0_mint_started'
  | 'mock_usdt0_mint_success'
  | 'payment_started'
  | 'payment_verify_success'
  | 'settlement_submitted'
  | 'settlement_confirmed'
  | 'unlock_success'
  | 'resource_download_pdf'
  | 'resource_download_md'
  | 'receipt_created'
  | 'verify_clicked'
  | 'feedback_submitted'
  | 'error';

export function trackEvent(event: AnalyticsEvent, properties?: Record<string, unknown>): void {
  try {
    const db = getDb();
    db.prepare('INSERT INTO analytics_events (id, event, properties) VALUES (?, ?, ?)').run(
      randomUUID(),
      event,
      properties ? JSON.stringify(properties) : null,
    );
  } catch {
    // analytics must never throw
  }
}
