import { notFound } from "next/navigation";
import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { ButtonLink } from "@/components/ui/Button";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import type { AssignmentTeam, Client } from "@/lib/clients";
import { ActivityPage, activityQuery, parseActivityFilters } from "@/lib/activities";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import { TrackingPanel } from "@/components/history/TrackingPanel";

import { ClientDetailPanel } from "./client-detail-panel";
import { ClientAssignments } from "./client-assignments";
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
  const activityFilters = parseActivityFilters(query);
  const activities = await serverApi<ActivityPage>(
    `/clients/${clientId}/activities?${activityQuery(activityFilters)}`,
    { notFoundOnDenied: true },
  );

  return (
    <AppShell active="clients" workspace={workspace}>
      <Link className={styles.back} href="/clients"><span aria-hidden="true">←</span> Volver a clientes</Link>
      <header className={styles.header}>
        <Eyebrow>Ficha de cliente</Eyebrow>
        <h1>{client.name}</h1>
        <MutedText>Datos generales y personas de contacto de la organización.</MutedText>
        {canManage ? <div className={styles.headerActions}>
          <ButtonLink href={`/summaries?client_id=${client.id}`}>
            Generar resumen de actividad con IA <span aria-hidden="true">→</span>
          </ButtonLink>
        </div> : null}
      </header>
      <ClientDetailPanel client={client} canManage={canManage} />
      <TrackingPanel
        key={`${activityFilters.view}:${activityFilters.type}:${activityFilters.department}:${activities.items
          .map((item) => `${item.id}:${item.updated_at}`)
          .join(",")}`}
        clientId={client.id}
        page={activities}
        filters={activityFilters}
      />
      {team ? <ClientAssignments clientId={client.id} team={team} scoped={workspace.user_role === "ADMIN"} /> : null}
    </AppShell>
  );
}
