export * from "./contracts";

export type ReceiptsPage = {
  items: Array<{
    id: string;
    status: string;
    amount: string;
    currency: string;
    chain: string;
    reference: string;
    created_at: string;
    anchored_at: string | null;
  }>;
  total: number;
  page: number;
  page_size: number;
};

export type ListReceiptsParams = {
  status?: string;
  chain?: string;
  reference?: string;
  since?: string;
  until?: string;
  scope?: "mine" | "all";
  page?: number;
  page_size?: number;
};

export type ReceiptResponse = {
  id: string;
  status: string;
  bundle_hash?: string | null;
  flare_txid?: string | null;
  xml_url?: string | null;
  bundle_url?: string | null;
  created_at: string;
  anchored_at?: string | null;
  [k: string]: any;
};

export type ChainAnchor = {
  chain: string;
  txid: string;
  anchored_at?: string | null;
};

export type ProjectAnchoringChain = {
  name: string;
  contract: string;
  rpc_url?: string | null;
  explorer_base_url?: string | null;
};

export type ProjectConfig = {
  anchoring: {
    execution_mode: "platform" | "tenant";
    chains: ProjectAnchoringChain[];
  };
};

export type ConfirmAnchorRequest = {
  receipt_id: string;
  chain?: string;
  flare_txid: string;
};

export type ConfirmAnchorResponse = {
  receipt_id: string;
  status: string;
  flare_txid?: string | null;
  anchored_at?: string | null;
};

export type VerifyResponse = {
  matches_onchain?: boolean;
  bundle_hash?: string;
  flare_txid?: string | null;
  anchored_at?: string | null;
  errors?: string[];
  [k: string]: any;
};

export type RefundRequest = {
  original_receipt_id: string;
  reason_code?: string;
};

export type RefundResponse = {
  refund_receipt_id: string;
  status: string;
};

// ── Agent types ───────────────────────────────────────────────────────────────

export type AgentCreate = {
  name: string;
  wallet_address: string;
  xmtp_address?: string;
  pricing_rules?: Record<string, string>;
  project_id?: string;
};

export type AgentUpdate = {
  name?: string;
  wallet_address?: string;
  xmtp_address?: string;
  pricing_rules?: Record<string, string>;
  status?: string;
};

export type AgentResponse = {
  id: string;
  name: string;
  wallet_address: string;
  xmtp_address?: string | null;
  pricing_rules?: Record<string, string> | null;
  status: string;
  project_id?: string | null;
  ai_mode: string;
  created_at: string;
  updated_at?: string | null;
};

export type AgentAnchoringConfig = {
  auto_anchor_enabled?: boolean;
  anchor_on_payment?: boolean;
  anchor_wallet_address?: string;
  anchor_private_key?: string;
};

export type AgentAnchoringConfigResponse = {
  id: string;
  auto_anchor_enabled: boolean;
  anchor_on_payment: boolean;
  anchor_wallet: string | null;
};

export type AgentAnchorDataRequest = {
  data: Record<string, unknown>;
  description?: string;
  chain?: string;
  submit_onchain?: boolean;
};

export type AgentAnchorDataResponse = {
  id: string;
  agent_id: string;
  anchor_hash: string;
  chain: string;
  status: string;
  submit_onchain: boolean;
  description?: string | null;
  created_at?: string | null;
};

export type AgentAnchorRecord = {
  id: string;
  bundle_hash: string;
  anchor_txid?: string | null;
  chain: string;
  status: string;
  anchored_at?: string | null;
  created_at?: string | null;
};

export type X402PaymentRecord = {
  id: string;
  tx_hash: string;
  amount: string;
  currency: string;
  chain: string;
  endpoint: string;
  verified_at: string;
  anchor_txid?: string | null;
  anchor_status?: string | null;
};

export type RevenueResponse = {
  total_revenue: string;
  payment_count: number;
  days: number;
  by_endpoint: Array<{ endpoint: string; count: number; revenue: string }>;
};

export type ISOClientOptions = {
  baseUrl: string;
  apiKey?: string;
};

function joinUrl(baseUrl: string, path: string): string {
  const b = baseUrl.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return b + p;
}

export default class IsoMiddlewareClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(opts: ISOClientOptions) {
    this.baseUrl = opts.baseUrl;
    this.apiKey = opts.apiKey;
  }

  private headers(extra?: HeadersInit): HeadersInit {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) h["X-API-Key"] = this.apiKey;
    return { ...h, ...(extra as any) };
  }

  async listReceipts(params: ListReceiptsParams = {}): Promise<ReceiptsPage> {
    const url = new URL(joinUrl(this.baseUrl, "/v1/receipts"));
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      url.searchParams.set(k, String(v));
    });
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`listReceipts_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async getReceipt(receiptId: string): Promise<ReceiptResponse> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/iso/receipts/${receiptId}`), {
      headers: this.headers(),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`getReceipt_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async getAnchors(receiptId: string): Promise<ChainAnchor[]> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/anchors/${receiptId}`), {
      headers: this.headers(),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`getAnchors_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async confirmAnchor(req: ConfirmAnchorRequest): Promise<ConfirmAnchorResponse> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/iso/confirm-anchor"), {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`confirmAnchor_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async getProjectConfig(projectId: string): Promise<ProjectConfig> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/projects/${projectId}/config`), {
      headers: this.headers(),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`getProjectConfig_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async putProjectConfig(projectId: string, cfg: ProjectConfig): Promise<ProjectConfig> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/projects/${projectId}/config`), {
      method: "PUT",
      headers: this.headers(),
      body: JSON.stringify(cfg),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`putProjectConfig_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async verifyBundle(req: { bundle_url?: string; bundle_hash?: string }): Promise<VerifyResponse> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/iso/verify"), {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`verify_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async verifyCid(req: { cid: string; store?: "ipfs" | "arweave" | "auto"; receipt_id?: string }): Promise<VerifyResponse> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/iso/verify-cid"), {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`verify_cid_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async camt053(date: string): Promise<{ status: string; date: string; count: number; url?: string }> {
    const url = new URL(joinUrl(this.baseUrl, "/v1/iso/statements/camt053"));
    url.searchParams.set("date", date);
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`camt053_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async camt052(
    date: string,
    window: string
  ): Promise<{ status: string; date: string; window: string; count: number; url?: string }> {
    const url = new URL(joinUrl(this.baseUrl, "/v1/iso/statements/camt052"));
    url.searchParams.set("date", date);
    url.searchParams.set("window", window);
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`camt052_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  async refund(req: RefundRequest): Promise<RefundResponse> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/iso/refund"), {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`refund_failed:${r.status}:${txt}`);
    }
    return r.json();
  }

  // ── Agent CRUD ──────────────────────────────────────────────────────────────

  async createAgent(req: AgentCreate): Promise<AgentResponse> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/agents"), {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) throw new Error(`createAgent_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async listAgents(): Promise<AgentResponse[]> {
    const r = await fetch(joinUrl(this.baseUrl, "/v1/agents"), { headers: this.headers() });
    if (!r.ok) throw new Error(`listAgents_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async getAgent(agentId: string): Promise<AgentResponse> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/agents/${agentId}`), {
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`getAgent_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async updateAgent(agentId: string, req: AgentUpdate): Promise<AgentResponse> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/agents/${agentId}`), {
      method: "PUT",
      headers: this.headers(),
      body: JSON.stringify(req),
    });
    if (!r.ok) throw new Error(`updateAgent_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async deleteAgent(agentId: string): Promise<void> {
    const r = await fetch(joinUrl(this.baseUrl, `/v1/agents/${agentId}`), {
      method: "DELETE",
      headers: this.headers(),
    });
    if (!r.ok) throw new Error(`deleteAgent_failed:${r.status}:${await r.text().catch(() => "")}`);
  }

  // ── Agent anchoring ─────────────────────────────────────────────────────────

  async getAgentAnchoringConfig(agentId: string): Promise<AgentAnchoringConfigResponse> {
    const r = await fetch(
      joinUrl(this.baseUrl, `/v1/agents/${agentId}/anchoring-config`),
      { headers: this.headers() },
    );
    if (!r.ok) throw new Error(`getAgentAnchoringConfig_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async updateAgentAnchoringConfig(
    agentId: string,
    cfg: AgentAnchoringConfig,
  ): Promise<AgentAnchoringConfigResponse> {
    const r = await fetch(
      joinUrl(this.baseUrl, `/v1/agents/${agentId}/anchoring-config`),
      { method: "PUT", headers: this.headers(), body: JSON.stringify(cfg) },
    );
    if (!r.ok) throw new Error(`updateAgentAnchoringConfig_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async anchorAgentData(
    agentId: string,
    req: AgentAnchorDataRequest,
  ): Promise<AgentAnchorDataResponse> {
    const r = await fetch(
      joinUrl(this.baseUrl, `/v1/agents/${agentId}/anchor-data`),
      { method: "POST", headers: this.headers(), body: JSON.stringify(req) },
    );
    if (!r.ok) throw new Error(`anchorAgentData_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async listAgentAnchors(agentId: string, days = 7): Promise<AgentAnchorRecord[]> {
    const url = new URL(joinUrl(this.baseUrl, `/v1/agents/${agentId}/anchors`));
    url.searchParams.set("days", String(days));
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) throw new Error(`listAgentAnchors_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  // ── x402 analytics ─────────────────────────────────────────────────────────

  async listX402Payments(limit = 50): Promise<X402PaymentRecord[]> {
    const url = new URL(joinUrl(this.baseUrl, "/v1/x402/payments"));
    url.searchParams.set("limit", String(limit));
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) throw new Error(`listX402Payments_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  async getX402Revenue(days = 7): Promise<RevenueResponse> {
    const url = new URL(joinUrl(this.baseUrl, "/v1/x402/revenue"));
    url.searchParams.set("days", String(days));
    const r = await fetch(url.toString(), { headers: this.headers() });
    if (!r.ok) throw new Error(`getX402Revenue_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }

  // ── Receipt status (lightweight polling) ───────────────────────────────────

  async getReceiptStatus(receiptId: string): Promise<{
    id: string; status: string; bundle_hash?: string | null;
    flare_txid?: string | null; anchored_at?: string | null;
  }> {
    const r = await fetch(
      joinUrl(this.baseUrl, `/v1/iso/receipts/${receiptId}/status`),
      { headers: this.headers() },
    );
    if (!r.ok) throw new Error(`getReceiptStatus_failed:${r.status}:${await r.text().catch(() => "")}`);
    return r.json();
  }
}
