import { NextRequest, NextResponse } from "next/server";
import { demoRead, demoWrite } from "@/lib/demo-store";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (process.env.DEMO_MODE === "true") {
    const endpoint = `/${path.join("/")}${request.nextUrl.search}`;
    if (["GET", "HEAD"].includes(request.method)) return demoRead(endpoint, request.cookies.get("crm_demo_session")?.value);
    const origin = request.headers.get("origin");
    const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
    if (origin && host && new URL(origin).host !== host) return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
    const payload = await request.json().catch(() => ({}));
    const result = await demoWrite(endpoint, request.method, payload, request.cookies.get("crm_demo_session")?.value);
    const response = new NextResponse(result.response.body, { status: result.response.status,
      headers: { "content-type": result.response.headers.get("content-type") ?? "application/json" } });
    response.cookies.set("crm_demo_session", result.sessionId, { httpOnly: true, sameSite: "lax", path: "/",
      secure: request.nextUrl.protocol === "https:", maxAge: 24 * 60 * 60 });
    return response;
  }
  const upstreamUrl = new URL(`/api/v1/${path.join("/")}`, backendUrl);
  upstreamUrl.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["content-type", "cookie", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });
  const outgoing = new NextResponse(response.body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
  for (const cookie of response.headers.getSetCookie()) outgoing.headers.append("set-cookie", cookie);
  return outgoing;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
