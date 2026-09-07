import { AppShell } from "@/components/layout/AppShell";
import { TasksPanel } from "@/components/tasks/TasksPanel";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import { TaskPage, parseTaskFilters, taskApiQuery } from "@/lib/tasks";
import { loadWorkspace, serverApi } from "@/lib/workspace";
import styles from "./page.module.css";

export default async function MyTasksPage({ searchParams }: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const workspace = await loadWorkspace();
  const filters = parseTaskFilters(await searchParams ?? {});
  const page = await serverApi<TaskPage>(`/tasks/mine?${taskApiQuery(filters)}`);
  return <AppShell active="tasks" workspace={workspace}>
    <header className={styles.header}><Eyebrow>Seguimiento</Eyebrow><h1>Mis tareas</h1>
      <MutedText>Tareas de las que eres responsable. Puedes crear nuevas desde la ficha de cada cliente.</MutedText></header>
    <TasksPanel page={page} filters={filters} />
  </AppShell>;
}
