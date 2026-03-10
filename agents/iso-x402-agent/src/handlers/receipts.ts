import { ISOMiddlewareClient } from '../x402/client';

export async function handleListReceipts(
  client: ISOMiddlewareClient,
  args: Record<string, any>
): Promise<string> {
  try {
    const limit = args.limit || 10;
    const receipts = await client.listReceipts(limit);

    if (!receipts || receipts.length === 0) {
      return '📭 No receipts found.';
    }

    let response = `📋 **Recent Receipts** (${receipts.length}):\n\n`;

    for (const receipt of receipts) {
      response += `🧾 **${receipt.reference}**\n`;
      response += `   ID: \`${receipt.id}\`\n`;
      response += `   Amount: ${receipt.amount} ${receipt.currency}\n`;
      response += `   Status: ${receipt.status}\n`;
      response += `   Created: ${new Date(receipt.created_at).toLocaleString()}\n\n`;
    }

    return response.trim();
  } catch (error: any) {
    return `❌ Failed to list receipts: ${error.message}`;
  }
}

export async function handleGetReceipt(
  client: ISOMiddlewareClient,
  args: Record<string, any>
): Promise<string> {
  try {
    const { receiptId } = args;

    if (!receiptId) {
      return '❌ Please provide a receipt ID. Usage: `get <receipt_id>`';
    }

    const receipt = await client.getReceipt(receiptId);

    let response = `🧾 **Receipt Details**\n\n`;
    response += `**Reference:** ${receipt.reference}\n`;
    response += `**ID:** \`${receipt.id}\`\n`;
    response += `**Amount:** ${receipt.amount} ${receipt.currency}\n`;
    response += `**Status:** ${receipt.status}\n`;
    response += `**Chain:** ${receipt.chain}\n`;
    response += `**From:** \`${receipt.sender_wallet}\`\n`;
    response += `**To:** \`${receipt.receiver_wallet}\`\n`;
    response += `**Tx Hash:** \`${receipt.tip_tx_hash}\`\n`;
    response += `**Created:** ${new Date(receipt.created_at).toLocaleString()}\n`;

    if (receipt.anchored_at) {
      response += `**Anchored:** ${new Date(receipt.anchored_at).toLocaleString()}\n`;
    }

    if (receipt.bundle_hash) {
      response += `**Bundle Hash:** \`${receipt.bundle_hash}\`\n`;
    }

    return response.trim();
  } catch (error: any) {
    return `❌ Failed to get receipt: ${error.message}`;
  }
}
