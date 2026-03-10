export type StorePublic = {
  active_project_id?: string;
  projects: Array<{ id: string; name: string; owner_wallet: string; created_at: string }>;
};

export async function fetchStore(): Promise<StorePublic> {
  const r = await fetch("/api/store/projects", { cache: "no-store" });
  if (!r.ok) throw new Error(`store_fetch_failed: ${r.status}`);
  return r.json();
}
