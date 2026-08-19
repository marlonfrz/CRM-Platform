import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { loadWorkspace, serverApi } from "@/lib/workspace";

import { AdministrationPanel } from "./administration-panel";
import styles from "./page.module.css";

type Organization = { id: string; name: string; mode: "INDIVIDUAL" | "BUSINESS" };
type Department = { id: string; name: string };

export default async function AdministrationPage() {
  const workspace = await loadWorkspace();
  if (workspace.user_role === "EMPLOYEE") redirect("/dashboard");
  const [organization, departments] = await Promise.all([
    serverApi<Organization>("/admin/organization"),
    serverApi<Department[]>("/admin/departments"),
  ]);
  return (
    <AppShell active="administration" workspace={workspace}>
      <header className={styles.header}>
        <Eyebrow>Administración</Eyebrow>
        <h1>Organización y departamentos</h1>
        <MutedText>Configura la estructura sobre la que aplicaremos usuarios y permisos.</MutedText>
      </header>
      <AdministrationPanel
        canCreateDepartments={workspace.user_role === "OWNER"}
        canEditOrganization={workspace.user_role === "OWNER"}
        departments={departments}
        organization={organization}
      />
    </AppShell>
  );
}
