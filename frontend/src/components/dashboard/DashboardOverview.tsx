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
    { label: employee || individual ? "Mis clientes" : "Clientes del catálogo global", value: data.metrics.clients },
    { label: employee || individual ? "Mis tareas pendientes" : "Tareas pendientes en tu alcance", value: data.metrics.pending_tasks },
    { label: "Tareas completadas", value: data.metrics.completed_tasks },
    { label: "Actividades visibles", value: data.metrics.activities },
  ];
  if (management && data.metrics.active_users !== null && data.metrics.departments !== null) {
    metrics.push({ label: workspace.user_role === "OWNER" ? "Usuarios activos" : "Empleados activos de tu equipo", value: data.metrics.active_users },
      { label: "Departamentos", value: data.metrics.departments });
  }
  return <div className={styles.stack}>
    <div className={styles.metrics}>{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</div>
    <nav className={styles.links} aria-label="Accesos rápidos">
      <Link href="/clients">{employee || individual ? "Ver mis clientes" : "Abrir clientes"}</Link>
      <Link href="/tasks">Ver mis tareas</Link>
    </nav>
    <div className={styles.columns}>
      <Card className={styles.panel}><h2>Trabajo pendiente</h2>
        <MutedText>Hasta cinco tareas de tu alcance, ordenadas por fecha límite. Las que no tienen fecha quedan al final.</MutedText>
        <div className={styles.list}>{data.pending_tasks.map((entry) => <HistoryItem key={entry.id} entry={entry} compact showClient />)}
          {!data.pending_tasks.length ? <MutedText className={styles.empty}>No hay tareas pendientes en tu alcance.</MutedText> : null}
        </div>
      </Card>
      <Card className={styles.panel}><h2>Actividad reciente</h2>
        <MutedText>Las cinco interacciones más recientes que puedes consultar.</MutedText>
        <div className={styles.list}>{data.recent_activities.map((entry) => <HistoryItem key={entry.id} entry={entry} compact showClient />)}
          {!data.recent_activities.length ? <MutedText className={styles.empty}>Todavía no hay actividad visible.</MutedText> : null}
        </div>
      </Card>
    </div>
    {management ? <Card className={styles.panel}><h2>{workspace.user_role === "OWNER" ? "Departamentos de la organización" : "Departamentos que administras"}</h2>
      <div className={styles.departments}>{data.departments.map((department) => <section className={styles.department} key={department.id}>
        <h3>{department.name}</h3><dl>
          <div><dt>Empleados activos</dt><dd>{department.active_employees}</dd></div>
          <div><dt>Actividades visibles</dt><dd>{department.activities}</dd></div>
          <div><dt>Tareas pendientes</dt><dd>{department.pending_tasks}</dd></div>
        </dl>
      </section>)}</div>
      {!data.departments.length ? <MutedText>No hay departamentos disponibles.</MutedText> : null}
    </Card> : null}
  </div>;
}
