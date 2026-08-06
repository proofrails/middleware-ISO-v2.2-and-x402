import { NextResponse, type NextRequest } from "next/server";

import { getActiveProject, loadStore } from "lib/server/auth";

function apiBase(req: NextRequest): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE || process.env.API_BASE_URL;
  if (configured) return configured;

  // In production the API is served from the same origin as the app. Falling
  // back to localhost makes deployed verification calls fail with a blank 500.
  const isLocal = req.nextUrl.hostname === "localhost" || req.nextUrl.hostname === "127.0.0.1";
  return isLocal ? "http://127.0.0.1:8000" : req.nextUrl.origin;
}

function buildTargetUrl(req: NextRequest, pathParts: string[]): string {
  const base = apiBase(req).replace(/\/$/, "");
  const target = new URL(base + "/" + pathParts.join("/"));

  // Preserve querystring
  req.nextUrl.searchParams.forEach((v, k) => target.searchParams.set(k, v));
  return target.toString();
}

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;

  const targetUrl = buildTargetUrl(req, path);

  // Copy headers; do not forward cookies
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (k === "host" || k === "cookie") return;
    headers.set(key, value);
  });

  // Attach X-API-Key from active project if present
  const store = loadStore();
  const active = getActiveProject(store);
  if (active?.api_key) {
    headers.set("X-API-Key", active.api_key);
  }

  // Body
  const method = req.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await req.arrayBuffer();

  const upstream = await fetch(targetUrl, {
    method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });

  // Pass-through response
  const resHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    // Let Next set its own encoding/length
    if (k === "content-encoding" || k === "content-length") return;
    resHeaders.set(key, value);
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
