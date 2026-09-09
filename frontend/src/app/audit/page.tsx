import { redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { AuditPanel } from "@/components/audit/AuditPanel";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { AuditPage, auditQuery, parseAuditFilters } from "@/lib/audit";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import styles from "./page.module.css";

export default async function AuditPageView({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const workspace = await loadWorkspace();
  if (workspace.user_role !== "OWNER") redirect("/dashboard");
  const filters = parseAuditFilters(await searchParams ?? {});
  const invalidRange = Boolean(filters.since && filters.until && filters.since > filters.until);
  const page = invalidRange ? { items: [], has_more: false } : await serverApi<AuditPage>(`/audit?${auditQuery(filters, true)}`, { notFoundOnDenied: true });
  return <AppShell active="audit" workspace={workspace}>
    <header className={styles.header}><Eyebrow>Trazabilidad</Eyebrow><h1>Auditoría</h1>
      <MutedText>Quién hizo qué, sobre qué recurso y cuándo. Consulta exclusiva del propietario.</MutedText>
      <MutedText>Los nombres de los autores son los actuales. Los eventos se conservan sin borrado automático y no pueden editarse desde la aplicación.</MutedText>
    </header>
    <AuditPanel page={page} filters={filters} invalidRange={invalidRange} />
  </AppShell>;
}
