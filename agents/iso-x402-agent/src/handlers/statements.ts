import { ISOMiddlewareClient } from '../x402/client';

export async function handleGenerateStatement(
  client: ISOMiddlewareClient,
  args: Record<string, any>
): Promise<string> {
  try {
    const { date } = args;

    if (!date) {
      return '❌ Please provide a date. Usage: `statement <YYYY-MM-DD>`';
    }

    let response = '⏳ Generating statement (paying 0.005 USDC)...\n\n';

    const result = await client.generateStatement(date);

    response += '✅ **Statement Generated**\n\n';
    response += `**Type:** ${result.type}\n`;
    response += `**Date:** ${date}\n`;
    response += `**Transaction Count:** ${result.count}\n`;

    if (result.window) {
      response += `**Time Window:** ${result.window}\n`;
    }

    response += `\n💰 **Payment:** 0.005 USDC paid`;

    return response.trim();
  } catch (error: any) {
    return `❌ Statement generation failed: ${error.message}`;
  }
}
