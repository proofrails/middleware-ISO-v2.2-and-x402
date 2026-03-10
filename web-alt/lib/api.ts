import type { ReceiptsPage, VerifyResponse, ListReceiptsParams } from "iso-middleware-sdk";
import IsoMiddlewareClient from "iso-middleware-sdk";
export type { ReceiptsPage };

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
export type AIAssistResponse = {
  reply: string;
  used_tools?: Array<{ tool: string; ok: boolean }>;
};

// IMPORTANT: UI never talks to the backend directly; it uses Next Route Handlers as a proxy.
// This keeps API keys in httpOnly cookies, out of the browser bundle.
const BASE = "/api/proxy";

let _client: IsoMiddlewareClient | undefined;
function client(): IsoMiddlewareClient {
  if (!_client) {
    // SDK client will call /api/proxy/* which injects auth server-side.
    _client = new IsoMiddlewareClient({ baseUrl: BASE });
  }
  return _client;
}

function headers() {
  return { "Content-Type": "application/json" };
}

export async function listReceipts(params: ListReceiptsParams = {}): Promise<ReceiptsPage> {
  return client().listReceipts(params);
}

export async function aiAssist(body: AIAssistRequest): Promise<AIAssistResponse> {
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/ai/assist", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`ai_assist_failed: ${r.status} ${txt}`);
  }
  return r.json();
}

export async function verifyBundle(req: { bundle_url?: string; bundle_hash?: string }): Promise<VerifyResponse> {
  return client().verifyBundle(req);
}

export async function verifyCid(req: { cid: string; store?: "ipfs" | "arweave" | "auto"; receipt_id?: string }): Promise<VerifyResponse> {
  return client().verifyCid(req);
}

export async function downloadOpenApi(): Promise<Blob> {
  // Keep direct blob fetch for convenient download behavior in the UI
  const r = await fetch(BASE.replace(/\/$/, "") + "/openapi.json", { headers: headers() });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`openapi_fetch_failed: ${r.status} ${txt}`);
  }
  return r.blob();
}

export async function buildSdk(body: { lang: "ts" | "python"; base_url?: string; packaging?: "npm" | "pypi" | "none" }): Promise<{ blob: Blob; filename: string }> {
  // Meta endpoint on the backend; not part of public SDK surface
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/sdk/build", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`sdk_build_failed: ${r.status} ${txt}`);
  }
  const blob = await r.blob();
  const filename = body.lang === "ts" ? "iso-client-ts.zip" : "iso-client-py.zip";
  return { blob, filename };
}

export async function getConfig(): Promise<any> {
  // Admin-only (kept as direct call)
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/config", { headers: headers(), cache: "no-store" });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`config_fetch_failed: ${r.status} ${txt}`);
  }
  return r.json();
}

export async function putConfig(cfg: any): Promise<any> {
  // Admin-only (kept as direct call)
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/config", {
    method: "PUT",
    headers: headers(),
    body: JSON.stringify(cfg),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`config_save_failed: ${r.status} ${txt}`);
  }
  return r.json();
}

export async function camt053(date: string): Promise<{ status: string; date: string; count: number; url?: string }>{
  return client().camt053(date);
}

export async function camt052(date: string, window: string): Promise<{ status: string; date: string; window: string; count: number; url?: string }>{
  return client().camt052(date, window);
}

export async function getAIStatus(): Promise<{ enabled: boolean; provider: string; model: string; has_api_key: boolean; features: Record<string, boolean> }> {
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/ai/status", {
    headers: headers(),
    cache: "no-store"
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`ai_status_failed: ${r.status} ${txt}`);
  }
  return r.json();
}

export async function refund(req: { original_receipt_id: string; reason_code?: string }): Promise<{ refund_receipt_id: string; status: string }> {
  const r = await fetch(BASE.replace(/\/$/, "") + "/v1/iso/refund", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`refund_failed: ${r.status} ${txt}`);
  }
  return r.json();
}
