import axios, { AxiosInstance } from 'axios';
import { Wallet, Contract, parseUnits } from 'ethers';
import { logger } from '../utils/logger';

export interface ClientConfig {
  apiUrl: string;
  apiKey?: string;
  x402Recipient: string;
  chainRpcUrl: string;
  usdcContract: string;
  wallet: Wallet;
}

export class ISOMiddlewareClient {
  private api: AxiosInstance;
  private config: ClientConfig;
  private wallet: Wallet;

  constructor(config: ClientConfig) {
    this.config = config;
    this.wallet = config.wallet;

    this.api = axios.create({
      baseURL: config.apiUrl,
      headers: config.apiKey
        ? { 'X-API-Key': config.apiKey }
        : {},
    });
  }

  /**
   * Make a paid request to a premium endpoint
   */
  private async makePaidRequest(
    endpoint: string,
    price: string,
    method: 'GET' | 'POST' = 'POST',
    data?: any
  ) {
    try {
      // Step 1: Make payment
      logger.info(`Making payment of ${price} USDC for ${endpoint}...`);
      const txHash = await this.makePayment(price);
      logger.info(`Payment successful: ${txHash}`);

      // Step 2: Make API request with payment proof
      const headers = {
        'X-PAYMENT': JSON.stringify({
          tx_hash: txHash,
          amount: price,
          recipient: this.config.x402Recipient,
          currency: 'USDC',
          chain: 'base',
        }),
      };

      const response = await this.api.request({
        method,
        url: endpoint,
        data,
        headers,
      });

      return response.data;
    } catch (error: any) {
      logger.error('Paid request failed:', error.message);
      throw error;
    }
  }

  /**
   * Make a USDC payment on Base chain
   */
  private async makePayment(amountUSDC: string): Promise<string> {
    try {
      // In a real implementation, this would:
      // 1. Connect to Base chain
      // 2. Approve USDC spend
      // 3. Transfer USDC to recipient
      // 4. Wait for confirmation
      // 5. Return transaction hash

      // For demonstration purposes, we'll return a mock hash
      // In production, implement actual USDC transfer logic
      
      logger.warn('MOCK PAYMENT - Implement actual USDC transfer for production');
      
      const mockTxHash = `0x${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`;
      
      // Simulate payment delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      return mockTxHash;
    } catch (error: any) {
      logger.error('Payment failed:', error.message);
      throw new Error(`Payment failed: ${error.message}`);
    }
  }

  /**
   * List receipts (free endpoint)
   */
  async listReceipts(limit: number = 10) {
    const response = await this.api.get(`/v1/receipts?limit=${limit}`);
    return response.data;
  }

  /**
   * Get receipt by ID (free endpoint)
   */
  async getReceipt(receiptId: string) {
    const response = await this.api.get(`/v1/receipts/${receiptId}`);
    return response.data;
  }

  /**
   * Verify bundle (paid: 0.001 USDC)
   */
  async verifyBundle(bundleUrl: string) {
    return await this.makePaidRequest(
      '/v1/x402/premium/verify-bundle',
      '0.001',
      'POST',
      { bundle_url: bundleUrl }
    );
  }

  /**
   * Generate statement (paid: 0.005 USDC)
   */
  async generateStatement(date: string) {
    return await this.makePaidRequest(
      '/v1/x402/premium/generate-statement',
      '0.005',
      'POST',
      { date }
    );
  }

  /**
   * Initiate refund (paid: 0.003 USDC)
   */
  async initiateRefund(receiptId: string, reason: string) {
    return await this.makePaidRequest(
      '/v1/x402/premium/refund',
      '0.003',
      'POST',
      {
        receipt_id: receiptId,
        reason,
        return_method: 'REVERSAL',
      }
    );
  }
}
