import { ISOMiddlewareClient } from '../x402/client';

export async function handleRefund(
  client: ISOMiddlewareClient,
  args: Record<string, any>
): Promise<string> {
  try {
    const { receiptId, reason } = args;

    if (!receiptId) {
      return '❌ Please provide a receipt ID. Usage: `refund <receipt_id> [reason]`';
    }

    let response = '⏳ Initiating refund (paying 0.003 USDC)...\n\n';

    const result = await client.initiateRefund(receiptId, reason);

    response += '✅ **Refund Initiated**\n\n';
    response += `**Original Receipt:** \`${receiptId}\`\n`;
    response += `**Refund Receipt:** \`${result.refund_receipt_id}\`\n`;
    response += `**Method:** ${result.return_method}\n`;
    response += `**Reason:** ${reason}\n`;
    response += `**Status:** ${result.status}\n`;

    if (result.pacs004_path) {
      response += `**pacs.004:** ${result.pacs004_path}\n`;
    }

    response += `\n💰 **Payment:** 0.003 USDC paid`;

    return response.trim();
  } catch (error: any) {
    return `❌ Refund failed: ${error.message}`;
  }
}
