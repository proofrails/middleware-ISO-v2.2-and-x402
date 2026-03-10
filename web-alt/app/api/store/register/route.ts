import { NextResponse } from "next/server";

import { upsertProject, type StoredProject } from "lib/server/auth";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { name?: string; message?: string; signature?: string } | null;
  if (!body?.name || !body?.message || !body?.signature) {
    return NextResponse.json({ error: "missing_fields" }, { status: 400 });
  }

  const r = await fetch(apiBase().replace(/\/$/, "") + "/v1/projects/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: body.name, message: body.message, signature: body.signature }),
  });

  const txt = await r.text();
  if (!r.ok) {
    return new NextResponse(txt, { status: r.status, headers: { "Content-Type": r.headers.get("Content-Type") || "text/plain" } });
  }

  const data = JSON.parse(txt) as {
    project: { id: string; name: string; owner_wallet: string; created_at: string };
    api_key: string;
  };

  const stored: StoredProject = {
    id: data.project.id,
    name: data.project.name,
    owner_wallet: data.project.owner_wallet,
    created_at: data.project.created_at,
    api_key: data.api_key,
  };

  upsertProject(stored);

  // Return api_key once so user can copy it, but it is also stored server-side in httpOnly cookie.
  return NextResponse.json({ project: data.project, api_key: data.api_key });
}
