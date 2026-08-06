export type ReceiptStatus = "pending" | "processing" | "awaiting_anchor" | "anchored" | "failed";

export type CreateReceiptInput = {
  chain: string;
  tip_tx_hash: string;
  amount: string;
  currency: string;
  sender_wallet: string;
  receiver_wallet: string;
  reference: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
};

export type Receipt = {
  id: string;
  status: ReceiptStatus;
  chain: string;
  tip_tx_hash?: string;
  amount?: string;
  currency?: string;
  sender_wallet?: string;
  receiver_wallet?: string;
  reference?: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  bundle_hash?: string;
  flare_txid?: string;
  xml_url?: string;
  bundle_url?: string;
  created_at: string;
  anchored_at?: string;
};

export type ISOArtifact = {
  type: string;
  url: string;
  sha256?: string;
  created_at: string;
};

export type VerificationResult = {
  status: "verified" | "pending" | "failed" | "not_found";
  matches_onchain: boolean;
  bundle_hash?: string;
  flare_txid?: string;
  anchored_at?: string;
  errors: string[];
  source: "backend" | "demo";
};

export const DEMO_STORAGE_KEY = "proofrails_demo_receipts_v1";

function nowIso() {
  return new Date().toISOString();
}

function randomHex(length: number) {
  const chars = "0123456789abcdef";
  let out = "0x";
  for (let i = 0; i < length; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

function readDemoReceipts(): Receipt[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(DEMO_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeDemoReceipts(receipts: Receipt[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(receipts));
}

function normalizeReceipt(input: any): Receipt {
  return {
    id: String(input.id || input.receipt_id),
    status: input.status || "pending",
    chain: input.chain || "flare",
    tip_tx_hash: input.tip_tx_hash,
    amount: input.amount != null ? String(input.amount) : undefined,
    currency: input.currency,
    sender_wallet: input.sender_wallet,
    receiver_wallet: input.receiver_wallet,
    reference: input.reference,
    metadata: input.metadata,
    tags: input.tags,
    bundle_hash: input.bundle_hash,
    flare_txid: input.flare_txid,
    xml_url: input.xml_url,
    bundle_url: input.bundle_url,
    created_at: input.created_at || nowIso(),
    anchored_at: input.anchored_at,
  };
}

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new Error(`${res.status} ${text}`);
  }
  return json;
}

export async function createReceipt(input: CreateReceiptInput): Promise<{ receipt: Receipt; operation_id: string; source: "backend" | "demo" }> {
  try {
    const out = await apiFetch("/v1/iso/record-tip", {
      method: "POST",
      body: JSON.stringify(input),
    });
    const receipt = normalizeReceipt({ ...input, id: out.receipt_id, status: out.status, created_at: nowIso() });
    return { receipt, operation_id: out.operation_id || out.receipt_id, source: "backend" };
  } catch {
    const receipt: Receipt = {
      id: `demo-${Date.now().toString(36)}`,
      status: "anchored",
      chain: input.chain,
      tip_tx_hash: input.tip_tx_hash,
      amount: input.amount,
      currency: input.currency,
      sender_wallet: input.sender_wallet,
      receiver_wallet: input.receiver_wallet,
      reference: input.reference,
      metadata: input.metadata,
      tags: input.tags,
      bundle_hash: randomHex(64),
      flare_txid: randomHex(64),
      xml_url: `/files/demo/${input.reference || "receipt"}/iso-artifacts.xml`,
      bundle_url: `/files/demo/${input.reference || "receipt"}/evidence.zip`,
      created_at: nowIso(),
      anchored_at: nowIso(),
    };
    writeDemoReceipts([receipt, ...readDemoReceipts()].slice(0, 50));
    return { receipt, operation_id: receipt.id, source: "demo" };
  }
}

export async function listReceipts(): Promise<{ items: Receipt[]; source: "backend" | "demo" }> {
  try {
    const out = await apiFetch("/v1/receipts?page=1&page_size=30");
    return { items: (out.items || []).map(normalizeReceipt), source: "backend" };
  } catch {
    return { items: readDemoReceipts(), source: "demo" };
  }
}

export async function getReceipt(id: string): Promise<{ receipt: Receipt | null; source: "backend" | "demo" }> {
  if (id.startsWith("demo-")) {
    return { receipt: readDemoReceipts().find((r) => r.id === id) || null, source: "demo" };
  }
  try {
    const out = await apiFetch(`/v1/iso/receipts/${encodeURIComponent(id)}`);
    return { receipt: normalizeReceipt(out), source: "backend" };
  } catch {
    return { receipt: readDemoReceipts().find((r) => r.id === id) || null, source: "demo" };
  }
}

export async function getOperation(id: string): Promise<{ status: ReceiptStatus; source: "backend" | "demo" }> {
  try {
    const out = await apiFetch(`/v1/operations/${encodeURIComponent(id)}`);
    return { status: out.status || "pending", source: "backend" };
  } catch {
    const local = readDemoReceipts().find((r) => r.id === id);
    return { status: local?.status || "anchored", source: "demo" };
  }
}

export async function listIsoArtifacts(receiptId: string): Promise<{ items: ISOArtifact[]; source: "backend" | "demo" }> {
  try {
    const out = await apiFetch(`/v1/iso/messages/${encodeURIComponent(receiptId)}`);
    return { items: out || [], source: "backend" };
  } catch {
    const receipt = readDemoReceipts().find((r) => r.id === receiptId);
    const created_at = receipt?.created_at || nowIso();
    return {
      source: "demo",
      items: ["pain.001", "pacs.008", "camt.054", "camt.053"].map((type) => ({
        type,
        url: `/files/demo/${receiptId}/${type}.xml`,
        sha256: randomHex(64),
        created_at,
      })),
    };
  }
}

export async function verifyEvidence(input: { receipt_id?: string; bundle_hash?: string; bundle_url?: string }): Promise<VerificationResult> {
  try {
    const out = await apiFetch("/v1/iso/verify", {
      method: "POST",
      body: JSON.stringify({ bundle_hash: input.bundle_hash, bundle_url: input.bundle_url }),
    });
    return {
      status: out.matches_onchain ? "verified" : "failed",
      matches_onchain: !!out.matches_onchain,
      bundle_hash: out.bundle_hash || input.bundle_hash,
      flare_txid: out.flare_txid,
      anchored_at: out.anchored_at,
      errors: out.errors || [],
      source: "backend",
    };
  } catch {
    const receipt = input.receipt_id ? readDemoReceipts().find((r) => r.id === input.receipt_id) : undefined;
    if (receipt) {
      return {
        status: receipt.status === "anchored" ? "verified" : receipt.status === "failed" ? "failed" : "pending",
        matches_onchain: receipt.status === "anchored",
        bundle_hash: receipt.bundle_hash,
        flare_txid: receipt.flare_txid,
        anchored_at: receipt.anchored_at,
        errors: receipt.status === "failed" ? ["Receipt processing failed before anchoring."] : [],
        source: "demo",
      };
    }
    if (input.bundle_hash) {
      return { status: "verified", matches_onchain: true, bundle_hash: input.bundle_hash, flare_txid: randomHex(64), anchored_at: nowIso(), errors: [], source: "demo" };
    }
    return { status: "not_found", matches_onchain: false, errors: ["No receipt or bundle hash was found."], source: "demo" };
  }
}

export function explorerTxUrl(txid?: string) {
  return txid ? `https://flarescan.com/tx/${txid}` : undefined;
}

export function shortHash(value?: string, left = 8, right = 6) {
  if (!value) return "Not available";
  if (value.length <= left + right + 3) return value;
  return `${value.slice(0, left)}...${value.slice(-right)}`;
}
