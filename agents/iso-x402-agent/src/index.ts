import dotenv from 'dotenv';
import { ISOAgent } from './agent';
import { logger } from './utils/logger';

dotenv.config();

async function main() {
  try {
    logger.info('Starting ISO Middleware x402 Agent...');
    
    const agent = new ISOAgent({
      walletPrivateKey: process.env.WALLET_PRIVATE_KEY!,
      xmtpEnv: process.env.XMTP_ENV as 'dev' | 'production' || 'dev',
      isoMwApiUrl: process.env.ISO_MW_API_URL || 'http://localhost:8000',
      isoMwApiKey: process.env.ISO_MW_API_KEY,
      x402Recipient: process.env.X402_RECIPIENT!,
      chainRpcUrl: process.env.CHAIN_RPC_URL || 'https://mainnet.base.org',
      usdcContract: process.env.USDC_CONTRACT || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
      agentName: process.env.AGENT_NAME || 'ISO Middleware Agent',
    });

    await agent.start();
    
    logger.info('Agent started successfully. Listening for messages...');

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      logger.info('Shutting down agent...');
      await agent.stop();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logger.info('Shutting down agent...');
      await agent.stop();
      process.exit(0);
    });
  } catch (error) {
    logger.error('Failed to start agent:', error);
    process.exit(1);
  }
}

main();
