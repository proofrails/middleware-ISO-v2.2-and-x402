import { NextResponse } from "next/server";

import { loadStore, setActiveProject } from "lib/server/auth";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { project_id?: string } | null;
  if (!body?.project_id) return NextResponse.json({ error: "missing_project_id" }, { status: 400 });

  setActiveProject(body.project_id);
  const store = loadStore();

  // Never leak API keys to the browser.
  return NextResponse.json({
    active_project_id: store.active_project_id,
    projects: store.projects.map((p) => ({
      id: p.id,
      name: p.name,
      owner_wallet: p.owner_wallet,
      created_at: p.created_at,
    })),
  });
}
