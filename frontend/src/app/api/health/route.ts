import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  if (process.env.DEMO_MODE === "true") return NextResponse.json({ status: "ok" });
  const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${backendUrl}/api/v1/health/ready`, {
      cache: "no-store",
    });
    const body: unknown = await response.json();

    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 503 });
  }
}
