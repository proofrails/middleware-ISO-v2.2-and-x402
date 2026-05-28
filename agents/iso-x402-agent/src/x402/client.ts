import axios, { AxiosInstance } from 'axios';
import { JsonRpcProvider, Wallet, Contract, parseUnits } from 'ethers';
import { logger } from '../utils/logger';

export interface ClientConfig {
  apiUrl: string;
  apiKey?: string;
  x402Recipient: string;
  chainRpcUrl: string;
  usdcContract: string;
  wallet: Wallet;
}

// Minimal ERC-20 ABI for USDC transfer
const ERC20_ABI = [
  'function transfer(address to, uint256 amount) returns (bool)',
  'function decimals() view returns (uint8)',
];

// Set X402_MOCK_PAYMENTS=true in .env to bypass real payment in dev/test.
// In production this must be false (or unset) — mock hashes never verify on-chain.
const MOCK_PAYMENTS = process.env.X402_MOCK_PAYMENTS === 'true';

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
   * Make a USDC payment on Base chain and return the confirmed tx hash.
   * Requires X402_MOCK_PAYMENTS=true for dev/test — never runs mock in production.
   */
  private async makePayment(amountUSDC: string): Promise<string> {
    if (MOCK_PAYMENTS) {
      logger.warn(
        'X402_MOCK_PAYMENTS=true — using deterministic test hash. ' +
        'This will fail payment verification in production.',
      );
      // Deterministic hash for tests: sha256-like prefix + amount encoded
      const mockHash =
        '0xdead0000' +
        Buffer.from(amountUSDC).toString('hex').padEnd(56, '0').slice(0, 56);
      return mockHash;
    }

    // Production: execute real ERC-20 transfer on Base
    const provider = new JsonRpcProvider(this.config.chainRpcUrl);
    const signer = this.wallet.connect(provider);
    const usdc = new Contract(this.config.usdcContract, ERC20_ABI, signer);

    // USDC uses 6 decimal places
    const decimals: number = await usdc.decimals();
    const amount = parseUnits(amountUSDC, decimals);

    logger.info(`Sending ${amountUSDC} USDC to ${this.config.x402Recipient}…`);
    const tx = await (usdc as any).transfer(this.config.x402Recipient, amount);
    const receipt = await tx.wait(1);

    if (!receipt || receipt.status !== 1) {
      throw new Error(`USDC transfer failed: tx ${tx.hash}`);
    }

    logger.info(`Payment confirmed: ${tx.hash}`);
    return tx.hash as string;
  }

  /**
   * Make a paid POST request with X-PAYMENT header.
   */
  private async makePaidRequest(
    endpoint: string,
    price: string,
    method: 'GET' | 'POST' = 'POST',
    data?: unknown,
  ) {
    logger.info(`Making payment of ${price} USDC for ${endpoint}…`);
    const txHash = await this.makePayment(price);
    logger.info(`Payment hash: ${txHash}`);

    const headers = {
      'X-PAYMENT': JSON.stringify({
        tx_hash: txHash,
        amount: price,
        recipient: this.config.x402Recipient,
        currency: 'USDC',
        chain: 'base',
      }),
    };

    const response = await this.api.request({ method, url: endpoint, data, headers });
    return response.data;
  }

  // ── Free endpoints ────────────────────────────────────────────────────────

  /**
   * List receipts. Returns paginated response: { items, total, page, page_size, next_cursor }.
   */
  async listReceipts(limit = 10): Promise<{ items: unknown[]; total: number; next_cursor?: string }> {
    const response = await this.api.get(`/v1/receipts?page_size=${limit}`);
    // Backend returns { items: [...], total: ..., page: ..., page_size: ..., next_cursor: ... }
    return response.data;
  }

  /**
   * Get a single receipt by ID.
   */
  async getReceipt(receiptId: string) {
    // Correct path: /v1/iso/receipts/{id} (not /v1/receipts/{id})
    const response = await this.api.get(`/v1/iso/receipts/${receiptId}`);
    return response.data;
  }

  // ── Paid endpoints ────────────────────────────────────────────────────────

  /**
   * Verify an evidence bundle. Price: 0.001 USDC.
   */
  async verifyBundle(bundleUrl: string) {
    return this.makePaidRequest(
      '/v1/x402/premium/verify-bundle',
      '0.001',
      'POST',
      { bundle_url: bundleUrl },
    );
  }

  /**
   * Generate a camt.052/053 statement. Price: 0.005 USDC.
   * @param date  YYYY-MM-DD
   * @param window  Optional time window for camt.052 (e.g. "09:00-17:00").
   *                Omit for full-day camt.053.
   */
  async generateStatement(date: string, window?: string) {
    // Send as JSON body — backend expects StatementRequest schema
    return this.makePaidRequest(
      '/v1/x402/premium/generate-statement',
      '0.005',
      'POST',
      { date, window: window ?? '00:00-23:59' },
    );
  }

  /**
   * Initiate a payment refund. Price: 0.003 USDC.
   * @param receiptId  The receipt to refund (maps to original_receipt_id)
   * @param reasonCode  Optional ISO reason code
   */
  async initiateRefund(receiptId: string, reasonCode?: string) {
    // Correct schema: { original_receipt_id, reason_code } — not receipt_id/reason/return_method
    return this.makePaidRequest(
      '/v1/x402/premium/refund',
      '0.003',
      'POST',
      {
        original_receipt_id: receiptId,
        reason_code: reasonCode ?? 'CUST',
      },
    );
  }
}
