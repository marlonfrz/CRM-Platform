import Link from "next/link";
import { MutedText } from "@/components/ui/Text";
import { activityTypes, ActivityType } from "@/lib/activities";
import { formatUtcTimestamp } from "@/lib/date-time";
import { HistoryEntry } from "@/lib/insights";
import styles from "./HistoryItem.module.css";

export function HistoryItem({ entry, compact = false, showClient = false }: {
  entry: HistoryEntry; compact?: boolean; showClient?: boolean;
}) {
  const activity = entry.kind === "ACTIVITY";
  const title = activity ? activityTypes[entry.type as ActivityType] ?? "Actividad" : entry.title;
  return <article className={styles.item}>
    <header className={styles.header}><div>
      <span className={styles.category}>{activity ? "Actividad" : entry.type === "COMPLETED" ? "Tarea completada" : "Tarea pendiente"}</span>
      <h3>{title}</h3>
    </div><time dateTime={entry.occurred_at}>{formatUtcTimestamp(entry.occurred_at)}</time></header>
    {showClient ? <Link className={styles.link} href={`/clients/${entry.client_id}#${activity ? "activities" : "tasks"}`}>{entry.client_name}</Link> : null}
    <MutedText>{activity ? "Autor" : "Responsable"}: {entry.person_name}{entry.department_name ? ` · ${entry.department_name}` : ""}</MutedText>
    {entry.description ? <p className={compact ? styles.excerpt : styles.description}>{entry.description}</p> : null}
    {!compact && entry.next_action ? <div className={styles.nextAction}><strong>Próxima acción</strong><p>{entry.next_action}</p></div> : null}
    {!activity ? <MutedText>{entry.due_at ? `Fecha límite: ${formatUtcTimestamp(entry.due_at)}` : "Sin fecha límite"}</MutedText> : null}
  </article>;
}
