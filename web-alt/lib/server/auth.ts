import { cookies } from "next/headers";

export type StoredProject = {
  id: string;
  name: string;
  owner_wallet: string;
  created_at: string;
  api_key: string;
};

type Store = {
  active_project_id?: string;
  projects: StoredProject[];
};

const COOKIE_NAME = "iso_projects";

function safeJsonParse<T>(s: string | undefined | null): T | null {
  if (!s) return null;
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

export function loadStore(): Store {
  const raw = cookies().get(COOKIE_NAME)?.value;
  const parsed = safeJsonParse<Store>(raw);
  if (parsed && Array.isArray(parsed.projects)) return parsed;
  return { projects: [] };
}

export function saveStore(store: Store) {
  // httpOnly to keep keys out of JS runtime. SameSite Lax to work locally.
  cookies().set(COOKIE_NAME, JSON.stringify(store), {
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export function clearStore() {
  cookies().set(COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
    maxAge: 0,
  });
}

export function getActiveProject(store = loadStore()): StoredProject | null {
  const activeId = store.active_project_id;
  if (activeId) {
    const p = store.projects.find((x) => x.id === activeId);
    if (p) return p;
  }
  // fallback to first
  return store.projects[0] ?? null;
}

export function setActiveProject(projectId: string): Store {
  const s = loadStore();
  const exists = s.projects.some((p) => p.id === projectId);
  if (!exists) return s;
  s.active_project_id = projectId;
  saveStore(s);
  return s;
}

export function upsertProject(p: StoredProject): Store {
  const s = loadStore();
  const idx = s.projects.findIndex((x) => x.id === p.id);
  if (idx >= 0) s.projects[idx] = p;
  else s.projects.unshift(p);
  s.active_project_id = p.id;
  saveStore(s);
  return s;
}

export function removeProject(projectId: string): Store {
  const s = loadStore();
  s.projects = s.projects.filter((p) => p.id !== projectId);
  if (s.active_project_id === projectId) {
    s.active_project_id = s.projects[0]?.id;
  }
  saveStore(s);
  return s;
}
