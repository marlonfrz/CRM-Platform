import type { ReactNode } from "react";
import Link from "next/link";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { Eyebrow } from "@/components/ui/Text";
import type { Workspace } from "@/lib/workspace";

import styles from "./AppShell.module.css";

type AppShellProps = {
  active: "dashboard" | "clients" | "administration" | "tasks";
  children: ReactNode;
  workspace: Workspace;
};

export function AppShell({ active, children, workspace }: AppShellProps) {
  const canAdminister = workspace.user_role !== "EMPLOYEE" && workspace.organization_mode === "BUSINESS";
  return (
    <main className={styles.shell}>
      <aside className={styles.sidebar}>
        <div><Eyebrow>CRM Platform</Eyebrow><h2>{workspace.organization_name}</h2></div>
        <nav className={styles.navigation} aria-label="Navegación principal">
          <a className={`${styles.item} ${active === "dashboard" ? styles.active : ""}`} href="/dashboard">Resumen</a>
          <Link className={`${styles.item} ${active === "clients" ? styles.active : ""}`} href="/clients">{workspace.user_role === "EMPLOYEE" ? "Mis clientes" : "Clientes"}</Link>
          <Link className={`${styles.item} ${active === "tasks" ? styles.active : ""}`} href="/tasks">Mis tareas</Link>
          {canAdminister ? (
            <a className={`${styles.item} ${active === "administration" ? styles.active : ""}`} href="/administration">Administración</a>
          ) : null}
        </nav>
        <LogoutButton className={styles.logout} />
      </aside>
      <section className={styles.content}>{children}</section>
    </main>
  );
}
