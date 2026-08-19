import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { loadWorkspace, serverApi } from "@/lib/workspace";

import { AdministrationPanel } from "./administration-panel";
import styles from "./page.module.css";

type Department = { id: string; name: string };

export default async function AdministrationPage() {
  const workspace = await loadWorkspace();
  if (workspace.user_role === "EMPLOYEE" || workspace.organization_mode === "INDIVIDUAL") redirect("/dashboard");
  const departments = await serverApi<Department[]>("/admin/departments");
  return (
    <AppShell active="administration" workspace={workspace}>
      <header className={styles.header}>
        <Eyebrow>Administración</Eyebrow>
        <h1>Administración</h1>
        <MutedText>Gestiona la estructura interna de tu equipo.</MutedText>
      </header>
      <AdministrationPanel
        canCreateDepartments={workspace.user_role === "OWNER"}
        departments={departments}
      />
    </AppShell>
  );
}
