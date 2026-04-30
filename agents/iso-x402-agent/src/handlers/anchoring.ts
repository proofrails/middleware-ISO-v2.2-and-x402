import { ISOMiddlewareClient } from '../x402/client';
import { logger } from '../utils/logger';

/**
 * Handle "anchor <json>" — hash arbitrary JSON data and queue an on-chain anchor.
 * The agent must have anchor_wallet_address configured on the backend.
 */
export async function handleAnchorData(
  client: ISOMiddlewareClient,
  agentId: string,
  args: string[],
): Promise<string> {
  const raw = args.join(' ').trim();

  if (!raw) {
    return (
      'Usage: anchor <json_data>\n' +
      'Example: anchor {"payment_id":"pay-001","amount":100}\n\n' +
      'The data is hashed (SHA-256 canonical JSON) and the hash is submitted on-chain.\n' +
      'Raw data is never stored.'
    );
  }

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(raw);
  } catch {
    return 'Invalid JSON. Ensure the data is valid JSON.\nExample: anchor {"key":"value"}';
  }

  try {
    const response = await (client as any).api.post(
      `/v1/agents/${agentId}/anchor-data`,
      { data, submit_onchain: true },
    );
    const r = response.data;
    return (
      `Anchor queued.\n` +
      `Hash:   ${r.anchor_hash}\n` +
      `Chain:  ${r.chain}\n` +
      `Status: ${r.status}\n` +
      `ID:     ${r.id}`
    );
  } catch (err: any) {
    logger.error('anchor command error:', err?.message);
    return `Error anchoring data: ${err?.response?.data?.detail ?? err?.message ?? 'unknown error'}`;
  }
}

/**
 * Handle "list anchors [days]" — list recent anchor records for this agent.
 */
export async function handleListAnchors(
  client: ISOMiddlewareClient,
  agentId: string,
  args: string[],
): Promise<string> {
  const days = parseInt(args[0] ?? '7', 10) || 7;

  try {
    const response = await (client as any).api.get(
      `/v1/agents/${agentId}/anchors?days=${days}`,
    );
    const anchors: any[] = response.data;

    if (!anchors.length) {
      return `No anchors in the last ${days} day(s).`;
    }

    const lines = anchors.map((a, i) =>
      [
        `${i + 1}. ${a.bundle_hash?.slice(0, 14)}…`,
        `   Chain: ${a.chain}  Status: ${a.status}`,
        a.anchor_txid ? `   Tx:    ${a.anchor_txid}` : null,
        `   Created: ${a.created_at}`,
      ]
        .filter(Boolean)
        .join('\n'),
    );

    return `Anchors (last ${days} day(s)):\n\n${lines.join('\n\n')}`;
  } catch (err: any) {
    logger.error('list anchors error:', err?.message);
    return `Error listing anchors: ${err?.message ?? 'unknown error'}`;
  }
}

/**
 * Handle "verify anchor <hash>" — check whether an anchor hash is confirmed on-chain.
 */
export async function handleVerifyAnchor(
  client: ISOMiddlewareClient,
  agentId: string,
  args: string[],
): Promise<string> {
  const hash = args[0];
  if (!hash) {
    return 'Usage: verify anchor <hash>\nExample: verify anchor 0xabc123…';
  }

  try {
    const response = await (client as any).api.get(
      `/v1/agents/${agentId}/anchors`,
    );
    const anchors: any[] = response.data;
    const match = anchors.find((a) => a.bundle_hash === hash);

    if (!match) {
      return `No anchor found for hash: ${hash}`;
    }

    return (
      `Anchor found.\n` +
      `Hash:       ${match.bundle_hash}\n` +
      `Status:     ${match.status}\n` +
      `Chain:      ${match.chain}\n` +
      (match.anchor_txid ? `Tx:         ${match.anchor_txid}\n` : '') +
      (match.anchored_at ? `Anchored at: ${match.anchored_at}` : '')
    );
  } catch (err: any) {
    logger.error('verify anchor error:', err?.message);
    return `Error verifying anchor: ${err?.message ?? 'unknown error'}`;
  }
}
