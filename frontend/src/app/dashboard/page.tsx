import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Card } from "@/components/ui/Card";
import { Eyebrow, MutedText } from "@/components/ui/Text";

import { LogoutButton } from "./logout-button";
import styles from "./page.module.css";

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
    <main className={styles.shell}>
      <aside className={styles.sidebar}>
        <div>
          <Eyebrow>CRM Platform</Eyebrow>
          <h2>{workspace.organization_name}</h2>
        </div>
        <nav aria-label="Navegación principal">
          <a className={`${styles.navItem} ${styles.active}`} href="/dashboard">Resumen</a>
          <span className={`${styles.navItem} ${styles.disabled}`}>Clientes <small>Próximamente</small></span>
          {workspace.organization_mode === "BUSINESS" ? (
            <span className={`${styles.navItem} ${styles.disabled}`}>Equipo <small>Próximamente</small></span>
          ) : null}
        </nav>
        <LogoutButton className={styles.logout} />
      </aside>
      <section className={styles.content}>
        <header className={styles.header}>
          <div>
            <Eyebrow>Resumen</Eyebrow>
            <h1>Hola, {workspace.user_name}</h1>
            <MutedText>Ya estás dentro del espacio protegido del CRM.</MutedText>
          </div>
          <span className={styles.roleBadge}>{workspace.user_role}</span>
        </header>
        <div className={styles.metricGrid}>
          <Card className={styles.metricCard}><span>Organización</span><strong>{workspace.organization_name}</strong></Card>
          <Card className={styles.metricCard}><span>Modalidad</span><strong>{workspace.organization_mode === "INDIVIDUAL" ? "Personal" : "Empresa"}</strong></Card>
          <Card className={styles.metricCard}><span>Departamentos asignados</span><strong>{workspace.departments.length}</strong></Card>
        </div>
        <Card className={styles.sessionCard}>
          <div><Eyebrow>Sesión activa</Eyebrow><h2>{workspace.user_email}</h2></div>
          <MutedText className={styles.sessionDescription}>La autenticación, la renovación de sesión y el alcance de permisos se validan en el backend.</MutedText>
        </Card>
      </section>
    </main>
  );
}
