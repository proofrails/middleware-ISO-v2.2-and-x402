import { NextResponse } from "next/server";

import { loadStore, removeProject } from "lib/server/auth";

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  removeProject(id);
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
