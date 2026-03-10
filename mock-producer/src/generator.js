import { customAlphabet } from "nanoid";

/**
 * Schedules and sends synthetic tips to the Middleware API.
 * Non-invasive: does not change the middleware or web UIs.
 */
export class MockGenerator {
  /**
   * @param {{
   *   mw: { recordTip: (payload:any)=>Promise<any> },
   *   onSent?: ()=>void,
   *   onError?: ()=>void,
   *   onStart?: (rate:number)=>void,
   *   onStop?: ()=>void,
   * }} deps
   */
  constructor(deps) {
    this.mw = deps.mw;
    this.onSent = deps.onSent || (() => {});
    this.onError = deps.onError || (() => {});
    this.onStart = deps.onStart || (() => {});
    this.onStop = deps.onStop || (() => {});

    this._timer = null;
    this._startedAt = null;
    this._sent = 0;
    this._errors = 0;
    this._params = null;
    this._stopTimeout = null;

    // Generators
    this.nano = customAlphabet("1234567890abcdef", 16);
  }

  /**
   * Build a single payload (ensures dedupe-safety).
   * @param {{
   *   chain: string,
   *   currency: string,
   *   amount?: string,
   *   reference?: string,
   *   sender_wallet?: string,
   *   receiver_wallet?: string,
   *   includeCallback?: boolean,
   *   referencePrefix?: string
   * }} opt
   */
  async buildPayload(opt) {
    const now = Date.now();
    const rand = this.nano();
    const tip_tx_hash = "0x" + this.nano() + this.nano();
    const reference = opt.reference || `${opt.referencePrefix || "demo:tip:"}${now}:${rand}`;
    const sender_wallet = opt.sender_wallet || ("0xS" + this.nano().padStart(40, "0")).slice(0, 42);
    const receiver_wallet = opt.receiver_wallet || ("0xR" + this.nano().padStart(40, "0")).slice(0, 42);

    const payload = {
      tip_tx_hash,
      chain: opt.chain,
      amount: opt.amount || this._randomAmount(),
      currency: opt.currency,
      sender_wallet,
      receiver_wallet,
      reference,
    };

    if (opt.includeCallback && typeof window === "undefined") {
      // Server-side callback URL (only if configured in mock-producer)
      // NOTE: The caller (server.js) decides to pass includeCallback when CALLBACK_BASE_URL is set.
      // The server exposes POST /callback; we append a path here.
      payload.callback_url = `${process.env.CALLBACK_BASE_URL?.replace(/\/$/, "") || ""}/callback`;
    }

    return payload;
  }

  /**
   * Start a scenario that posts tips at a given rate.
   * @param {{
   *   rate: number,                // tips per minute
   *   durationSec?: number,        // optional auto-stop
   *   chain: string,
   *   currency: string,
   *   amountMin: string,
   *   amountMax: string,
   *   seed?: string,               // reserved for future deterministic modes
   *   failurePct?: number,         // reserved (client-side failure simulation)
   *   referencePrefix?: string,
   *   includeCallback?: boolean
   * }} params
   */
  async start(params) {
    this.stop(); // stop any previous scenario

    const rate = Math.max(1, Number(params.rate || 30));
    const intervalMs = Math.max(200, Math.floor(60000 / rate));

    this._params = { ...params, rate, intervalMs };
    this._startedAt = new Date().toISOString();
    this._sent = 0;
    this._errors = 0;

    this._timer = setInterval(() => {
      this._emitOnce().catch(() => {});
    }, intervalMs);

    if (params.durationSec && Number(params.durationSec) > 0) {
      this._stopTimeout = setTimeout(() => this.stop(), Number(params.durationSec) * 1000);
    }

    this.onStart(rate);
  }

  stop() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
    if (this._stopTimeout) {
      clearTimeout(this._stopTimeout);
      this._stopTimeout = null;
    }
    if (this._params) {
      this.onStop();
    }
    this._params = null;
  }

  reset() {
    this._sent = 0;
    this._errors = 0;
  }

  status() {
    return {
      running: !!this._timer,
      startedAt: this._startedAt,
      sent: this._sent,
      errors: this._errors,
      params: this._params,
    };
  }

  async _emitOnce() {
    if (!this._params) return;

    try {
      const payload = await this.buildPayload({
        chain: this._params.chain,
        currency: this._params.currency,
        amount: this._randBetween(this._params.amountMin, this._params.amountMax),
        referencePrefix: this._params.referencePrefix,
        includeCallback: this._params.includeCallback,
      });

      await this.mw.recordTip(payload);
      this._sent += 1;
      this.onSent();
    } catch (e) {
      this._errors += 1;
      this.onError();
      // keep running; errors are counted for metrics
    }
  }

  _randomAmount() {
    // default: 0.000000000000000001 .. 5.000000000000000000
    const min = 1e-18;
    const max = 5.0;
    const v = Math.random() * (max - min) + min;
    return v.toFixed(18);
  }

  _randBetween(minStr, maxStr) {
    const min = Number(minStr || "0.000000000000000001");
    const max = Number(maxStr || "5.000000000000000000");
    const v = Math.random() * (max - min) + min;
    return v.toFixed(18);
  }
}
