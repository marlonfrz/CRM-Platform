import { AppShell } from "@/components/layout/AppShell";
import { DashboardOverview } from "@/components/dashboard/DashboardOverview";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { Dashboard } from "@/lib/insights";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import styles from "./page.module.css";

export default async function DashboardPage() {
  const workspace = await loadWorkspace();
  const data = await serverApi<Dashboard>("/dashboard");
  const individual = workspace.organization_mode === "INDIVIDUAL";
  const description = individual ? "Tus clientes, tareas y actividad, sin departamentos ni jerarquías."
    : workspace.user_role === "OWNER" ? "Visión global de los clientes, equipos y trabajo de tu organización."
    : workspace.user_role === "ADMIN" ? "Catálogo global de clientes y trabajo autorizado de los departamentos que administras."
    : "Tus clientes asignados, tus tareas y la actividad que puedes consultar.";
  return <AppShell active="dashboard" workspace={workspace}>
    <header className={styles.header}><Eyebrow>{individual ? "Resumen personal" : "Resumen de trabajo"}</Eyebrow>
      <h1>Hola, {workspace.user_name}</h1><MutedText>{description}</MutedText>
    </header>
    <DashboardOverview data={data} workspace={workspace} />
  </AppShell>;
}
