"use client";

import { useEffect, useState } from "react";
import type { StorePublic } from "./store";
import { fetchStore } from "./store";

export type UseProjectStoreResult = {
  store: StorePublic | null;
  activeProject: StorePublic["projects"][number] | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useProjectStore(): UseProjectStoreResult {
  const [store, setStore] = useState<StorePublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setLoading(true);
      setError(null);
      const s = await fetchStore();
      setStore(s);
    } catch (e: any) {
      setError(String(e?.message || e));
      setStore({ projects: [] });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh().catch(() => void 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeProject = (() => {
    if (!store?.projects?.length) return null;
    if (store.active_project_id) {
      return store.projects.find((p) => p.id === store.active_project_id) || store.projects[0] || null;
    }
    return store.projects[0] || null;
  })();

  return { store, activeProject, loading, error, refresh };
}
