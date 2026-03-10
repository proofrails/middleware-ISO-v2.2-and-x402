import express from "express";
import dotenv from "dotenv";
import { register, collectDefaultMetrics, Counter, Gauge } from "prom-client";
import { MockGenerator } from "./generator.js";
import { MwClient } from "./client.js";

dotenv.config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT ? Number(process.env.PORT) : 4001;

// Middleware API config (read from env; can be updated via /config)
let CONFIG = {
  MW_BASE_URL: process.env.MW_BASE_URL || "http://127.0.0.1:8000",
  API_KEY: process.env.API_KEY || "",
  DEFAULT_CHAIN: process.env.DEFAULT_CHAIN || "flare",
  DEFAULT_CURRENCY: process.env.DEFAULT_CURRENCY || "FLR",
  CALLBACK_BASE_URL: process.env.CALLBACK_BASE_URL || "", // if set, we pass callback_url in record-tip requests
};

const mw = new MwClient(() => CONFIG);

// Metrics
collectDefaultMetrics({ register });
const sentCounter = new Counter({
  name: "mock_producer_tips_sent_total",
  help: "Total number of tips sent to middleware",
});
const errCounter = new Counter({
  name: "mock_producer_errors_total",
  help: "Total number of errors from middleware post attempts",
});
const runningGauge = new Gauge({
  name: "mock_producer_running",
  help: "1 when a scenario is running, else 0",
});
const rateGauge = new Gauge({
  name: "mock_producer_rate_per_min",
  help: "Current configured rate (tips per minute) when running",
});

// Generator instance
const generator = new MockGenerator({
  mw,
  onSent: () => sentCounter.inc(),
  onError: () => errCounter.inc(),
  onStart: (rate) => {
    runningGauge.set(1);
    rateGauge.set(rate);
  },
  onStop: () => {
    runningGauge.set(0);
    rateGauge.set(0);
  },
});

// Routes
app.get("/health", (_req, res) => {
  res.json({ status: "ok", ts: new Date().toISOString(), version: "0.1.0" });
});

app.get("/metrics", async (_req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

// Scenario control
app.post("/scenarios/start", async (req, res) => {
  try {
    const {
      rate = 30, // tips/min
      durationSec, // optional duration
      chain,
      currency,
      amountMin,
      amountMax,
      seed,
      failurePct = 0,
      callback = false,
      referencePrefix = "demo:tip:",
    } = req.body || {};

    await generator.start({
      rate: Number(rate),
      durationSec: durationSec != null ? Number(durationSec) : undefined,
      chain: chain || CONFIG.DEFAULT_CHAIN,
      currency: currency || CONFIG.DEFAULT_CURRENCY,
      amountMin: amountMin != null ? String(amountMin) : "0.000000000000000001",
      amountMax: amountMax != null ? String(amountMax) : "5.000000000000000000",
      seed: seed || undefined,
      failurePct: Number(failurePct) || 0,
      referencePrefix: String(referencePrefix),
      includeCallback: Boolean(callback) && !!CONFIG.CALLBACK_BASE_URL,
    });

    res.json({ status: "started", params: generator.status().params });
  } catch (e) {
    res.status(400).json({ error: String(e?.message || e) });
  }
});

app.post("/scenarios/stop", (_req, res) => {
  generator.stop();
  res.json({ status: "stopped" });
});

app.get("/status", (_req, res) => {
  res.json(generator.status());
});

// Send a single tip
app.post("/one", async (req, res) => {
  try {
    const payload = await generator.buildPayload({
      chain: req.body?.chain || CONFIG.DEFAULT_CHAIN,
      currency: req.body?.currency || CONFIG.DEFAULT_CURRENCY,
      amount: req.body?.amount || "0.000000000000000001",
      reference: req.body?.reference,
      sender_wallet: req.body?.sender_wallet,
      receiver_wallet: req.body?.receiver_wallet,
      includeCallback: Boolean(req.body?.callback) && !!CONFIG.CALLBACK_BASE_URL,
      referencePrefix: req.body?.referencePrefix || "demo:tip:",
    });
    const resp = await mw.recordTip(payload);
    sentCounter.inc();
    res.json({ status: "ok", payload, middleware_response: resp.data });
  } catch (e) {
    errCounter.inc();
    res.status(500).json({ error: String(e?.message || e) });
  }
});

// Replay exact items
app.post("/replay", async (req, res) => {
  try {
    const items = Array.isArray(req.body?.items) ? req.body.items : [];
    const results = [];
    for (const it of items) {
      try {
        const resp = await mw.recordTip(it);
        sentCounter.inc();
        results.push({ ok: true, item: it, response: resp.data });
      } catch (e) {
        errCounter.inc();
        results.push({ ok: false, item: it, error: String(e?.message || e) });
      }
    }
    res.json({ status: "done", count: results.length, results });
  } catch (e) {
    res.status(400).json({ error: String(e?.message || e) });
  }
});

// Reset generator counters
app.post("/reset", (_req, res) => {
  generator.reset();
  res.json({ status: "reset" });
});

// Runtime config update (safe subset)
app.post("/config", (req, res) => {
  const allowed = ["MW_BASE_URL", "API_KEY", "DEFAULT_CHAIN", "DEFAULT_CURRENCY", "CALLBACK_BASE_URL"];
  for (const k of allowed) {
    if (k in req.body) {
      CONFIG[k] = String(req.body[k] ?? "");
    }
  }
  res.json({ status: "ok", config: CONFIG });
});

// Receive callbacks if callback_url used in record-tip
app.post("/callback", (req, res) => {
  // Best-effort log for demo; a real integration would persist this
  console.log("[callback]", new Date().toISOString(), JSON.stringify(req.body));
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`[mock-producer] listening on http://localhost:${PORT}`);
  console.log(`[mock-producer] MW_BASE_URL=${CONFIG.MW_BASE_URL}`);
});
