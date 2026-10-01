import type { ReactNode } from "react";
import Link from "next/link";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { SessionHeartbeat } from "@/components/auth/SessionHeartbeat";
import { Eyebrow } from "@/components/ui/Text";
import type { Workspace } from "@/lib/workspace";

import styles from "./AppShell.module.css";

type AppShellProps = {
  active: "dashboard" | "clients" | "administration" | "tasks" | "audit" | "summaries";
  children: ReactNode;
  workspace: Workspace;
};

export function AppShell({ active, children, workspace }: AppShellProps) {
  const canAdminister = workspace.user_role !== "EMPLOYEE" && workspace.organization_mode === "BUSINESS";
  const roleLabel = { OWNER: "Propietario", ADMIN: "Administrador", EMPLOYEE: "Empleado" }[workspace.user_role];
  return (
    <main className={styles.shell}>
      <SessionHeartbeat />
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">CP</span>
          <div><Eyebrow>{process.env.DEMO_MODE === "true" ? "CRM Platform Demo" : "CRM Platform"}</Eyebrow><h2>{workspace.organization_name}</h2></div>
        </div>
        <nav className={styles.navigation} aria-label="Navegación principal">
          <a className={`${styles.item} ${active === "dashboard" ? styles.active : ""}`} href="/dashboard">Resumen</a>
          <Link className={`${styles.item} ${active === "clients" ? styles.active : ""}`} href="/clients">{workspace.user_role === "EMPLOYEE" ? "Mis clientes" : "Clientes"}</Link>
          <Link className={`${styles.item} ${active === "tasks" ? styles.active : ""}`} href="/tasks">Mis tareas</Link>
          {canAdminister ? (
            <a className={`${styles.item} ${active === "administration" ? styles.active : ""}`} href="/administration">Administración</a>
          ) : null}
          {workspace.user_role === "OWNER" ? <Link className={`${styles.item} ${active === "audit" ? styles.active : ""}`} href="/audit">Auditoría</Link> : null}
          {workspace.user_role !== "EMPLOYEE" ? <Link className={`${styles.item} ${active === "summaries" ? styles.active : ""}`} href="/summaries">Resúmenes IA</Link> : null}
        </nav>
        <div className={styles.account}>
          <span className={styles.avatar} aria-hidden="true">{workspace.user_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span>
          <div><strong>{workspace.user_name}</strong><span>{roleLabel}</span></div>
        </div>
        {process.env.DEMO_MODE !== "true" ? <LogoutButton className={styles.logout} /> : null}
      </aside>
      <section className={styles.content}>{children}</section>
    </main>
  );
}
