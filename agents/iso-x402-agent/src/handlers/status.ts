import { ISOMiddlewareClient } from '../x402/client';
import { logger } from '../utils/logger';

/**
 * Handle the "status <receipt_id>" command.
 * Returns lightweight status (no ISO blobs) for polling agents.
 */
export async function handleGetStatus(
  client: ISOMiddlewareClient,
  args: Record<string, any>,
): Promise<string> {
  const receiptId = args.receiptId ?? args[0];

  if (!receiptId) {
    return 'Usage: status <receipt_id>\nReturns current status, bundle_hash, and anchor txid.';
  }

  try {
    // Use the lightweight status endpoint to avoid pulling full ISO artifacts
    const response = await (client as any).api.get(
      `/v1/iso/receipts/${receiptId}/status`,
    );
    const s = response.data;

    const lines = [
      `Receipt: ${s.id}`,
      `Status:  ${s.status}`,
      s.bundle_hash ? `Bundle:  ${s.bundle_hash}` : null,
      s.flare_txid  ? `Anchor:  ${s.flare_txid}`  : null,
      s.anchored_at ? `Anchored at: ${s.anchored_at}` : null,
    ].filter(Boolean);

    return lines.join('\n');
  } catch (err: any) {
    logger.error('status command error:', err?.message);
    if (err?.response?.status === 404) {
      return `Receipt not found: ${receiptId}`;
    }
    return `Error fetching status: ${err?.message ?? 'unknown error'}`;
  }
}
