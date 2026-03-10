import { Client } from '@xmtp/xmtp-js';
import { Wallet } from 'ethers';
import { logger } from './utils/logger';
import { parseCommand, parseCommandWithAI } from './utils/parser';
import { ISOMiddlewareClient } from './x402/client';
import { handleListReceipts, handleGetReceipt } from './handlers/receipts';
import { handleVerifyBundle } from './handlers/verify';
import { handleGenerateStatement } from './handlers/statements';
import { handleRefund } from './handlers/refunds';
import { handleHelp } from './handlers/help';

export interface AgentConfig {
  walletPrivateKey: string;
  xmtpEnv: 'dev' | 'production';
  isoMwApiUrl: string;
  isoMwApiKey?: string;
  x402Recipient: string;
  chainRpcUrl: string;
  usdcContract: string;
  agentName: string;
}

export class ISOAgent {
  private wallet: Wallet;
  private xmtpClient: Client | null = null;
  private isoClient: ISOMiddlewareClient;
  private config: AgentConfig;
  private isRunning = false;

  constructor(config: AgentConfig) {
    this.config = config;
    this.wallet = new Wallet(config.walletPrivateKey);
    this.isoClient = new ISOMiddlewareClient({
      apiUrl: config.isoMwApiUrl,
      apiKey: config.isoMwApiKey,
      x402Recipient: config.x402Recipient,
      chainRpcUrl: config.chainRpcUrl,
      usdcContract: config.usdcContract,
      wallet: this.wallet,
    });

    logger.info(`Agent wallet: ${this.wallet.address}`);
  }

  async start() {
    try {
      // Initialize XMTP client
      logger.info('Initializing XMTP client...');
      this.xmtpClient = await Client.create(this.wallet, {
        env: this.config.xmtpEnv,
      });

      logger.info(`XMTP client initialized for: ${this.xmtpClient.address}`);

      // Start listening for messages
      this.isRunning = true;
      await this.listenForMessages();
    } catch (error) {
      logger.error('Failed to start agent:', error);
      throw error;
    }
  }

  async stop() {
    this.isRunning = false;
    logger.info('Agent stopped');
  }

  private async listenForMessages() {
    if (!this.xmtpClient) {
      throw new Error('XMTP client not initialized');
    }

    logger.info('Listening for messages...');

    const stream = await this.xmtpClient.conversations.streamAllMessages();

    for await (const message of stream) {
      if (!this.isRunning) break;

      try {
        // Skip messages from self
        if (message.senderAddress === this.xmtpClient.address) {
          continue;
        }

        logger.info(`Received message from ${message.senderAddress}: ${message.content}`);

        // Process the message
        await this.handleMessage(message);
      } catch (error) {
        logger.error('Error processing message:', error);
      }
    }
  }

  private async handleMessage(message: any) {
    try {
      // Try parsing with AI support
      const command = await parseCommandWithAI(
        message.content,
        process.env.AI_MODE || 'simple',
        this.config.isoMwApiUrl,
        process.env.AI_SYSTEM_PROMPT
      );

      if (!command) {
        await this.sendReply(message, '❌ Invalid command. Type "help" for available commands.');
        return;
      }

      logger.info(`Processing command: ${command.action} (AI mode: ${process.env.AI_MODE || 'simple'})`);

      let response: string;

      switch (command.action) {
        case 'help':
          response = await handleHelp();
          break;

        case 'list':
          response = await handleListReceipts(this.isoClient, command.args);
          break;

        case 'get':
          response = await handleGetReceipt(this.isoClient, command.args);
          break;

        case 'verify':
          response = await handleVerifyBundle(this.isoClient, command.args);
          break;

        case 'statement':
          response = await handleGenerateStatement(this.isoClient, command.args);
          break;

        case 'refund':
          response = await handleRefund(this.isoClient, command.args);
          break;

        default:
          response = '❌ Unknown command. Type "help" for available commands.';
      }

      await this.sendReply(message, response);
    } catch (error: any) {
      logger.error('Error handling message:', error);
      await this.sendReply(message, `❌ Error: ${error.message}`);
    }
  }

  private async sendReply(message: any, content: string) {
    try {
      if (!this.xmtpClient) return;

      const conversation = await this.xmtpClient.conversations.newConversation(
        message.senderAddress
      );

      await conversation.send(content);
      logger.info(`Sent reply to ${message.senderAddress}`);
    } catch (error) {
      logger.error('Error sending reply:', error);
    }
  }
}
