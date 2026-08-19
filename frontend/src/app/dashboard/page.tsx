import { Card } from "@/components/ui/Card";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { AppShell } from "@/components/layout/AppShell";
import { loadWorkspace } from "@/lib/workspace";
import styles from "./page.module.css";

export default async function DashboardPage() {
  const workspace = await loadWorkspace();
  return (
    <AppShell active="dashboard" workspace={workspace}>
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
    </AppShell>
  );
}
