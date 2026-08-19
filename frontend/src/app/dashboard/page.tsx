import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { LogoutButton } from "./logout-button";

type Workspace = {
  organization_name: string;
  organization_mode: "INDIVIDUAL" | "BUSINESS";
  user_name: string;
  user_email: string;
  user_role: "OWNER" | "ADMIN" | "EMPLOYEE";
  departments: { id: string; name: string }[];
};

async function loadWorkspace(): Promise<Workspace> {
  const cookieStore = await cookies();
  const response = await fetch(
    `${process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"}/api/v1/workspace`,
    { headers: { cookie: cookieStore.toString() }, cache: "no-store" },
  );
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error("Workspace could not be loaded");
  return response.json() as Promise<Workspace>;
}

export default async function DashboardPage() {
  const workspace = await loadWorkspace();
  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">CRM Platform</p>
          <h2>{workspace.organization_name}</h2>
        </div>
        <nav aria-label="Navegación principal">
          <a className="nav-item active" href="/dashboard">Resumen</a>
          <span className="nav-item disabled">Clientes <small>Próximamente</small></span>
          {workspace.organization_mode === "BUSINESS" ? (
            <span className="nav-item disabled">Equipo <small>Próximamente</small></span>
          ) : null}
        </nav>
        <LogoutButton />
      </aside>
      <section className="dashboard-content">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Resumen</p>
            <h1>Hola, {workspace.user_name}</h1>
            <p className="muted">Ya estás dentro del espacio protegido del CRM.</p>
          </div>
          <span className="role-badge">{workspace.user_role}</span>
        </header>
        <div className="metric-grid">
          <article className="metric-card"><span>Organización</span><strong>{workspace.organization_name}</strong></article>
          <article className="metric-card"><span>Modalidad</span><strong>{workspace.organization_mode === "INDIVIDUAL" ? "Personal" : "Empresa"}</strong></article>
          <article className="metric-card"><span>Departamentos asignados</span><strong>{workspace.departments.length}</strong></article>
        </div>
        <section className="content-card">
          <div><p className="eyebrow">Sesión activa</p><h2>{workspace.user_email}</h2></div>
          <p>La autenticación, la renovación de sesión y el alcance de permisos se validan en el backend.</p>
        </section>
      </section>
    </main>
  );
}
