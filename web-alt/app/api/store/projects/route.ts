import { NextResponse } from "next/server";

import { loadStore } from "lib/server/auth";

export async function GET() {
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
