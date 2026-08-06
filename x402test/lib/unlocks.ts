import { getDb } from './db';
import { randomUUID } from 'crypto';

export interface UnlockRecord {
  id: string;
  resource_id: string;
  wallet_address: string;
  chain_id: number;
  payment_id: string;
  settlement_tx_hash: string;
  token: string;
  amount_raw: string;
  recipient: string;
  status: string;
  receipt_id: string | null;
  bundle_hash: string | null;
  verify_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export function findByPaymentId(paymentId: string): UnlockRecord | undefined {
  const db = getDb();
  return db.prepare('SELECT * FROM unlocks WHERE payment_id = ?').get(paymentId.toLowerCase()) as UnlockRecord | undefined;
}

export function createUnlock(data: {
  resource_id: string;
  wallet_address: string;
  chain_id: number;
  payment_id: string;
  settlement_tx_hash: string;
  token: string;
  amount_raw: string;
  recipient: string;
}): UnlockRecord {
  const db = getDb();
  const id = randomUUID();
  db.prepare(`
    INSERT INTO unlocks
      (id, resource_id, wallet_address, chain_id, payment_id, settlement_tx_hash, token, amount_raw, recipient, status)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unlocked')
  `).run(
    id,
    data.resource_id,
    data.wallet_address.toLowerCase(),
    data.chain_id,
    data.payment_id.toLowerCase(),
    data.settlement_tx_hash.toLowerCase(),
    data.token.toLowerCase(),
    data.amount_raw,
    data.recipient.toLowerCase(),
  );
  return findByPaymentId(data.payment_id)!;
}

export function updateReceipt(paymentId: string, receipt: {
  receipt_id?: string;
  bundle_hash?: string;
  verify_url?: string;
}): void {
  const db = getDb();
  db.prepare(`
    UPDATE unlocks SET receipt_id = ?, bundle_hash = ?, verify_url = ?, updated_at = datetime('now')
    WHERE payment_id = ?
  `).run(receipt.receipt_id ?? null, receipt.bundle_hash ?? null, receipt.verify_url ?? null, paymentId.toLowerCase());
}
