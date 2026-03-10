import { NextResponse } from "next/server";

import { clearStore } from "lib/server/auth";

export async function POST() {
  clearStore();
  return NextResponse.json({ ok: true });
}
