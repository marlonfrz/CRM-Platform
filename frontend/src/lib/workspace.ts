import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { demoRead } from "@/lib/demo-store";

export type Workspace = {
  user_id: string;
  organization_name: string;
  organization_mode: "INDIVIDUAL" | "BUSINESS";
  user_name: string;
  user_email: string;
  user_role: "OWNER" | "ADMIN" | "EMPLOYEE";
  departments: { id: string; name: string }[];
};

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
