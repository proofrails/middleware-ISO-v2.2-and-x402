import { ISOMiddlewareClient } from '../x402/client';

export async function handleVerifyBundle(
  client: ISOMiddlewareClient,
  args: Record<string, any>
): Promise<string> {
  try {
    const { bundleUrl } = args;

    if (!bundleUrl) {
      return '❌ Please provide a bundle URL. Usage: `verify <bundle_url>`';
    }

    let response = '⏳ Verifying bundle (paying 0.001 USDC)...\n\n';

    const result = await client.verifyBundle(bundleUrl);

    response += '✅ **Verification Complete**\n\n';
    response += `**Valid:** ${result.valid ? '✓ Yes' : '✗ No'}\n`;
    
    if (result.bundle_hash) {
      response += `**Bundle Hash:** \`${result.bundle_hash}\`\n`;
    }

    if (result.anchor_tx) {
      response += `**Anchor Tx:** \`${result.anchor_tx}\`\n`;
    }

    if (result.chains) {
      response += `**Chains:** ${result.chains.join(', ')}\n`;
    }

    if (result.timestamp) {
      response += `**Timestamp:** ${new Date(result.timestamp).toLocaleString()}\n`;
    }

    if (!result.valid && result.error) {
      response += `\n**Error:** ${result.error}\n`;
    }

    response += `\n💰 **Payment:** 0.001 USDC paid`;

    return response.trim();
  } catch (error: any) {
    return `❌ Verification failed: ${error.message}`;
  }
}
