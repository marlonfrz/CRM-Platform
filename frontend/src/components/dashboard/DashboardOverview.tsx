import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { MutedText } from "@/components/ui/Text";
import { HistoryItem } from "@/components/history/HistoryItem";
import { Dashboard } from "@/lib/insights";
import { Workspace } from "@/lib/workspace";
import { MetricCard } from "./MetricCard";
import styles from "./DashboardOverview.module.css";

export function DashboardOverview({ data, workspace }: { data: Dashboard; workspace: Workspace }) {
  const individual = workspace.organization_mode === "INDIVIDUAL";
  const employee = workspace.user_role === "EMPLOYEE";
  const management = !individual && !employee;
  const metrics = [
    { label: "Clientes con actividad hoy", value: data.metrics.today_clients },
    { label: "Actividades de hoy", value: data.metrics.today_activities },
    { label: "Pendientes hoy", value: data.metrics.today_pending_tasks },
    { label: "Completadas hoy", value: data.metrics.completed_tasks },
  ];
  return <div className={styles.stack}>
    <div className={styles.metrics}>{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</div>
    <nav className={styles.links} aria-label="Accesos rápidos">
      <Link href="/clients">{employee || individual ? "Ver mis clientes" : "Abrir clientes"}</Link>
      <Link href="/tasks">Ver mis tareas</Link>
    </nav>
    <div className={styles.dashboardGrid}>
      <Card className={styles.panel}>
        <div className={styles.panelHeader}><h2>Actividad de hoy</h2><span>{data.today_activities.length} registros</span></div>
        <div className={styles.list}>{data.today_activities.map((entry) => <HistoryItem key={entry.id} entry={entry} compact showClient />)}
          {!data.today_activities.length ? <MutedText className={styles.empty}>No hay actividad registrada para hoy.</MutedText> : null}
        </div>
      </Card>
      <Card className={styles.panel}>
        <div className={styles.panelHeader}><h2>{management ? "Organización" : "Tu alcance"}</h2>
          <span>{management ? `${data.departments.length} departamentos` : `${data.metrics.clients} clientes`}</span></div>
        {management ? <div className={styles.departments}>{data.departments.map((department) => <section className={styles.department} key={department.id}>
          <div><h3>{department.name}</h3><span>{department.active_employees} {department.active_employees === 1 ? "empleado activo" : "empleados activos"}</span></div>
          <strong>{department.activities} {department.activities === 1 ? "actividad hoy" : "actividades hoy"}</strong>
        </section>)}</div> : <dl className={styles.scopeStats}>
          <div><dt>Clientes visibles</dt><dd>{data.metrics.clients}</dd></div>
          <div><dt>Seguimiento visible</dt><dd>{data.metrics.activities}</dd></div>
          <div><dt>Pendientes totales</dt><dd>{data.metrics.pending_tasks}</dd></div>
        </dl>}
        {management && !data.departments.length ? <MutedText>No hay departamentos disponibles.</MutedText> : null}
      </Card>
    </div>
  </div>;
}
