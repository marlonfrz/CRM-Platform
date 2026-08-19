import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export type Workspace = {
  user_id: string;
  organization_name: string;
  organization_mode: "INDIVIDUAL" | "BUSINESS";
  user_name: string;
  user_email: string;
  user_role: "OWNER" | "ADMIN" | "EMPLOYEE";
  departments: { id: string; name: string }[];
};

export async function serverApi<T>(path: string): Promise<T> {
  const cookieStore = await cookies();
  const response = await fetch(
    `${process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"}/api/v1${path}`,
    { headers: { cookie: cookieStore.toString() }, cache: "no-store" },
  );
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error(`Backend request failed: ${path}`);
  return response.json() as Promise<T>;
}

export function loadWorkspace() {
  return serverApi<Workspace>("/workspace");
}
