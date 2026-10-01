import { notFound, redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { AISettingsPanel } from "@/components/summaries/AISettingsPanel";
import { SummaryPanel } from "@/components/summaries/SummaryPanel";
import { FilterTabs } from "@/components/ui/FilterTabs";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { AIConfiguration, SummaryOptions } from "@/lib/summaries";
import { defaultSummaryPeriod } from "@/lib/summary-period";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import styles from "./page.module.css";

type AIView = "SUMMARY" | "SETTINGS";

export default async function SummariesPage({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const workspace = await loadWorkspace();
  if (workspace.user_role === "EMPLOYEE") redirect("/dashboard");
  const query = await searchParams ?? {};
  const rawView = query.view;
  if (rawView !== undefined && rawView !== "SUMMARY" && rawView !== "SETTINGS") notFound();
  const view: AIView = rawView === "SETTINGS" ? "SETTINGS" : "SUMMARY";
  if (view === "SETTINGS" && workspace.user_role !== "OWNER") redirect("/summaries");

  const clientId = query.client_id;
  if (clientId !== undefined && (typeof clientId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clientId))) notFound();
  if (clientId && view === "SETTINGS") notFound();
  const client = clientId ? await serverApi<{ name: string }>(`/clients/${clientId}`, { notFoundOnDenied: true }) : null;
  const showTabs = workspace.user_role === "OWNER" && !client;
  const tabs = showTabs ? <FilterTabs label="Secciones de inteligencia artificial" activeValue={view}
    description={view === "SETTINGS"
      ? "Configura el proveedor, modelo y credenciales utilizados por la organización."
      : "Genera resúmenes basados únicamente en las actividades que puedes consultar."}
    items={[
      { value: "SUMMARY", label: "Resúmenes", href: "/summaries" },
      { value: "SETTINGS", label: "Opciones", href: "/summaries?view=SETTINGS" },
    ]} /> : null;

  if (view === "SETTINGS") {
    const configuration = await serverApi<AIConfiguration>("/ai/configuration", { notFoundOnDenied: true });
    return <AppShell active="summaries" workspace={workspace}>
      <header className={styles.header}><Eyebrow>Asistencia de IA</Eyebrow><h1>Opciones de IA</h1>
        <MutedText>El token se cifra en el servidor y nunca se devuelve después de guardarlo.</MutedText></header>
      <div className={styles.stack}>{tabs}<AISettingsPanel initialConfiguration={configuration} demo={process.env.DEMO_MODE === "true"} /></div>
    </AppShell>;
  }

  const options = await serverApi<SummaryOptions>("/ai/options", { notFoundOnDenied: true });
  const period = defaultSummaryPeriod();
  return <AppShell active="summaries" workspace={workspace}>
    <header className={styles.header}><Eyebrow>Asistencia de IA</Eyebrow><h1>{client ? `Resumen de ${client.name}` : "Resúmenes de actividad"}</h1>
      <MutedText>Información basada en tus registros, separada por departamento cuando corresponde. No sustituye tu revisión.</MutedText></header>
    <div className={styles.stack}>{tabs}<SummaryPanel key={clientId ?? "global"} options={options}
      demo={process.env.DEMO_MODE === "true"}
      individual={workspace.organization_mode === "INDIVIDUAL"} clientId={clientId as string | undefined}
      initialSince={period.since} initialUntil={period.until} /></div>
  </AppShell>;
}
