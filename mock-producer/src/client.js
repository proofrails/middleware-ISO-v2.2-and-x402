import axios from "axios";

/**
 * Lightweight Middleware API client.
 * Pass a getter to read dynamic config at call time (e.g., updated via /config).
 */
export class MwClient {
  /**
   * @param {() => { MW_BASE_URL: string, API_KEY?: string, CALLBACK_BASE_URL?: string }} getConfig
   */
  constructor(getConfig) {
    this.getConfig = getConfig;
  }

  _headers() {
    const { API_KEY } = this.getConfig();
    const h = { "Content-Type": "application/json" };
    if (API_KEY && String(API_KEY).trim() !== "") {
      h["X-API-Key"] = API_KEY;
    }
    return h;
  }

  baseUrl() {
    const { MW_BASE_URL } = this.getConfig();
    let b = (MW_BASE_URL || "").trim();
    if (!b) b = "http://127.0.0.1:8000";
    return b.replace(/\/$/, "");
  }

  /**
   * Posts a record-tip payload to the middleware.
   * @param {{
   *   tip_tx_hash: string,
   *   chain: string,
   *   amount: string,
   *   currency: string,
   *   sender_wallet: string,
   *   receiver_wallet: string,
   *   reference: string,
   *   callback_url?: string
   * }} payload
   */
  async recordTip(payload) {
    const url = `${this.baseUrl()}/v1/iso/record-tip`;
    return axios.post(url, payload, { headers: this._headers(), timeout: 20000 });
  }

  /**
   * Convenience helper to fetch a receipt by id (optional for debugging).
   * @param {string} id
   */
  async getReceipt(id) {
    const url = `${this.baseUrl()}/v1/iso/receipts/${id}`;
    return axios.get(url, { headers: this._headers(), timeout: 20000 });
  }

  /**
   * List receipts (optional for debugging).
   * @param {Record<string, string|number>} params
   */
  async listReceipts(params = {}) {
    const url = new URL(this.baseUrl() + "/v1/receipts");
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.append(k, String(v));
    });
    return axios.get(url.toString(), { headers: this._headers(), timeout: 20000 });
  }
}
