import { notFound } from "next/navigation";
import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import type { AssignmentTeam, Client } from "@/lib/clients";
import { ActivityPage, activityQuery, parseActivityFilters } from "@/lib/activities";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import { TasksPanel } from "@/components/tasks/TasksPanel";
import { TaskPage, parseTaskFilters, taskApiQuery } from "@/lib/tasks";

import { ClientDetailPanel } from "./client-detail-panel";
import { ClientAssignments } from "./client-assignments";
import { ClientActivities } from "./client-activities";
import styles from "./page.module.css";

type ClientPageProps = {
  params: Promise<{ clientId: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ClientPage({ params, searchParams }: ClientPageProps) {
  const workspace = await loadWorkspace();
  const { clientId } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clientId)) notFound();
  const client = await serverApi<Client>(`/clients/${clientId}`, { notFoundOnDenied: true });
  const canManage = workspace.user_role !== "EMPLOYEE";
  const team = canManage && workspace.organization_mode === "BUSINESS"
    ? await serverApi<AssignmentTeam>(`/clients/${clientId}/assignments`, { notFoundOnDenied: true })
    : null;
  const query = await searchParams ?? {};
  const filters = parseActivityFilters(query);
  const activities = await serverApi<ActivityPage>(`/clients/${clientId}/activities?${activityQuery(filters)}`, { notFoundOnDenied: true });
  const taskFilters = parseTaskFilters(query);
  const tasks = await serverApi<TaskPage>(`/clients/${clientId}/tasks?${taskApiQuery(taskFilters)}`, { notFoundOnDenied: true });

  return (
    <AppShell active="clients" workspace={workspace}>
      <Link className={styles.back} href="/clients"><span aria-hidden="true">←</span> Volver a clientes</Link>
      <header className={styles.header}>
        <Eyebrow>Ficha de cliente</Eyebrow>
        <h1>{client.name}</h1>
        <MutedText>Datos generales y personas de contacto de la organización.</MutedText>
      </header>
      <ClientDetailPanel client={client} canManage={canManage} />
      <ClientActivities clientId={client.id} page={activities} filters={filters} />
      <TasksPanel clientId={client.id} page={tasks} filters={taskFilters} preservedQuery={activityQuery(filters)} />
      {team ? <ClientAssignments clientId={client.id} team={team} scoped={workspace.user_role === "ADMIN"} /> : null}
    </AppShell>
  );
}
