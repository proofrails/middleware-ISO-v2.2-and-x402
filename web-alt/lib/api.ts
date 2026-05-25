import { listReceipts as listProofrailsReceipts, verifyEvidence } from "./proofrails";
import type { VerificationResult } from "./proofrails";

export type AIMessage = { role: "user" | "assistant" | "system"; content: string };
export type AIScope = {
  allow_read_receipts: boolean;
  allowed_receipt_ids: string[];
  allow_read_artifacts: boolean;
  allow_config_changes: boolean;
};
export type AIAssistRequest = {
  messages: AIMessage[];
  scope: AIScope;
  session_id?: string;
  params?: Record<string, any>;
};
export type AIAssistResponse = { reply: string; used_tools?: Array<{ tool: string; ok: boolean }> };
export type ReceiptsPage = { items: any[]; total: number; page: number; page_size: number; next_cursor?: string | null };
export type ListReceiptsParams = Record<string, any>;
export type VerifyResponse = VerificationResult;

const BASE = "/api/proxy";

function headers() {
  return { "Content-Type": "application/json" };
}

async function proxy(path: string, init?: RequestInit): Promise<any> {
  const r = await fetch(BASE + path, { ...init, headers: { ...headers(), ...(init?.headers || {}) }, cache: "no-store" });
  const text = await r.text().catch(() => "");
  if (!r.ok) throw new Error(`${r.status} ${text}`);
  return text ? JSON.parse(text) : null;
}

export async function listReceipts(_params: ListReceiptsParams = {}): Promise<ReceiptsPage> {
  const out = await listProofrailsReceipts();
  return { items: out.items, total: out.items.length, page: 1, page_size: out.items.length || 30, next_cursor: null };
}

export async function aiAssist(body: AIAssistRequest): Promise<AIAssistResponse> {
  try {
    return await proxy("/v1/ai/assist", { method: "POST", body: JSON.stringify(body) });
  } catch {
    return { reply: "ProofRails focuses this prototype on receipt creation, evidence bundles, and verification. Connect a backend to enable the assistant." };
  }
}

export async function verifyBundle(req: { bundle_url?: string; bundle_hash?: string }): Promise<VerifyResponse> {
  return verifyEvidence(req);
}

export async function verifyCid(req: { cid: string; store?: "ipfs" | "arweave" | "auto"; receipt_id?: string }): Promise<VerifyResponse> {
  return verifyEvidence({ receipt_id: req.receipt_id, bundle_hash: req.cid });
}

export async function downloadOpenApi(): Promise<Blob> {
  const r = await fetch(BASE + "/openapi.json", { cache: "no-store" });
  if (!r.ok) return new Blob([JSON.stringify({ openapi: "3.1.0", info: { title: "ProofRails", version: "prototype" } }, null, 2)], { type: "application/json" });
  return r.blob();
}

export async function buildSdk(body: { lang: "ts" | "python"; base_url?: string; packaging?: "npm" | "pypi" | "none" }): Promise<{ blob: Blob; filename: string }> {
  try {
    const r = await fetch(BASE + "/v1/sdk/build", { method: "POST", headers: headers(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return { blob: await r.blob(), filename: body.lang === "ts" ? "proofrails-sdk-ts.zip" : "proofrails-sdk-py.zip" };
  } catch {
    const text = body.lang === "ts" ? "// ProofRails SDK prototype\n" : "# ProofRails SDK prototype\n";
    return { blob: new Blob([text], { type: "text/plain" }), filename: body.lang === "ts" ? "proofrails-sdk.ts" : "proofrails_sdk.py" };
  }
}

export async function getConfig(): Promise<any> {
  try { return await proxy("/v1/config"); } catch { return { mode: "prototype", product: "ProofRails" }; }
}

export async function putConfig(cfg: any): Promise<any> {
  try { return await proxy("/v1/config", { method: "PUT", body: JSON.stringify(cfg) }); } catch { return cfg; }
}

export async function camt053(date: string): Promise<{ status: string; date: string; count: number; url?: string }>{
  return { status: "prototype", date, count: 0 };
}

export async function camt052(date: string, window: string): Promise<{ status: string; date: string; window: string; count: number; url?: string }>{
  return { status: "prototype", date, window, count: 0 };
}

export async function getAIStatus(): Promise<{ enabled: boolean; provider: string; model: string; has_api_key: boolean; features: Record<string, boolean> }> {
  return { enabled: false, provider: "prototype", model: "none", has_api_key: false, features: {} };
}

export async function refund(req: { original_receipt_id: string; reason_code?: string }): Promise<{ refund_receipt_id: string; status: string }> {
  return { refund_receipt_id: `refund-${req.original_receipt_id}`, status: "pending" };
}
