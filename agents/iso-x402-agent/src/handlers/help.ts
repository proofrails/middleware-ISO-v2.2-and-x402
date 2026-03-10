export async function handleHelp(): Promise<string> {
  return `
🤖 **ISO Middleware Agent - Available Commands**

📋 **Free Commands:**
• \`list [limit]\` - List recent receipts (default: 10)
• \`get <receipt_id>\` - Get receipt details
• \`help\` - Show this help message

💰 **Paid Commands (x402):**
• \`verify <bundle_url>\` - Verify evidence bundle (0.001 USDC)
• \`statement <date>\` - Generate statement (0.005 USDC)
• \`refund <receipt_id> [reason]\` - Initiate refund (0.003 USDC)

**Examples:**
\`list 5\` - List 5 most recent receipts
\`get abc123\` - Get receipt with ID abc123
\`verify https://ipfs.io/...\` - Verify a bundle
\`statement 2026-01-20\` - Generate statement for today
\`refund abc123 duplicate payment\` - Refund with reason

**Note:** Paid commands will automatically handle USDC payment via x402 protocol.
  `.trim();
}
