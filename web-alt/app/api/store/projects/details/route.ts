import { NextResponse } from "next/server";

import { loadStore } from "lib/server/auth";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}

export async function GET() {
  const store = loadStore();

  // Fetch each project's config using its stored API key.
  const projects = await Promise.all(
    store.projects.map(async (p) => {
      try {
        const r = await fetch(apiBase().replace(/\/$/, "") + `/v1/projects/${p.id}/config`, {
          headers: { "Content-Type": "application/json", "X-API-Key": p.api_key },
          cache: "no-store",
        });
        const txt = await r.text().catch(() => "");
        if (!r.ok) {
          return {
            id: p.id,
            name: p.name,
            owner_wallet: p.owner_wallet,
            created_at: p.created_at,
            ok: false,
            error: `config_fetch_failed:${r.status}:${txt}`,
            anchoring: null,
          };
        }
        const cfg = JSON.parse(txt) as any;
        return {
          id: p.id,
          name: p.name,
          owner_wallet: p.owner_wallet,
          created_at: p.created_at,
          ok: true,
          anchoring: cfg?.anchoring || null,
        };
      } catch (e: any) {
        return {
          id: p.id,
          name: p.name,
          owner_wallet: p.owner_wallet,
          created_at: p.created_at,
          ok: false,
          error: String(e?.message || e),
          anchoring: null,
        };
      }
    })
  );

  return NextResponse.json({ active_project_id: store.active_project_id, projects });
}
