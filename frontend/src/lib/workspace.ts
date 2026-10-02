import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { demoRead } from "@/lib/demo-store";
import type { WorkspaceResponse } from "@/lib/api-generated";

export type Workspace = WorkspaceResponse;

export async function serverApi<T>(path: string, options: { notFoundOnDenied?: boolean } = {}): Promise<T> {
  const cookieStore = await cookies();
  const response = process.env.DEMO_MODE === "true"
    ? demoRead(path, cookieStore.get("crm_demo_session")?.value)
    : await fetch(
    `${process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"}/api/v1${path}`,
    { headers: { cookie: cookieStore.toString() }, cache: "no-store" },
  );
  if (response.status === 401) redirect("/login");
  if (options.notFoundOnDenied && [403, 404].includes(response.status)) notFound();
  if (!response.ok) throw new Error(`Backend request failed: ${path}`);
  return response.json() as Promise<T>;
}

export function loadWorkspace() {
  return serverApi<Workspace>("/workspace");
}
