import Link from "next/link";

import { MutedText } from "@/components/ui/Text";
import { activityDate } from "@/lib/activities";
import { HistoryEntry } from "@/lib/insights";

import styles from "./HistoryItem.module.css";

export function HistoryItem({ entry, compact = false, showClient = false }: {
  entry: HistoryEntry;
  compact?: boolean;
  showClient?: boolean;
}) {
  return (
    <article className={styles.item}>
      <header className={styles.header}>
        <div>
          <span className={styles.category}>
            {entry.status === "PENDING" ? "Pendiente" : "Completada"}
          </span>
          <h3>{entry.title || entry.activity_type_name}</h3>
        </div>
        <time dateTime={entry.scheduled_for}>{activityDate(entry.scheduled_for)}</time>
      </header>
      {showClient ? (
        <Link className={styles.link} href={`/clients/${entry.client_id}#tracking`}>
          {entry.client_name}
        </Link>
      ) : null}
      <MutedText>
        Responsable: {entry.person_name}
        {entry.department_name ? ` · ${entry.department_name}` : ""}
      </MutedText>
      <p className={compact ? styles.excerpt : styles.description}>{entry.description}</p>
      {!compact && entry.next_action ? (
        <div className={styles.nextAction}>
          <strong>Próxima acción</strong><p>{entry.next_action}</p>
        </div>
      ) : null}
    </article>
  );
}
