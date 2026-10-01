import Link from "next/link";
import { activityDate } from "@/lib/activities";
import { formatUtcTimestamp } from "@/lib/date-time";
import type { SummarySource } from "@/lib/summaries";
import styles from "./SummarySourceItem.module.css";

export function SummarySourceItem({ source, cited }: { source: SummarySource; cited: boolean }) {
  return <li className={styles.item}>
    <strong>{source.title || source.activity_type_name}</strong>
    <div className={styles.meta}>
      {source.title ? <span>Tipo: {source.activity_type_name}</span> : null}
      <span>Cliente: <Link href={`/clients/${source.client_id}#tracking`}>{source.client_name}</Link></span>
      <time dateTime={source.occurred_at ?? source.scheduled_for}>
        {source.status === "PENDING" ? `Programada: ${activityDate(source.scheduled_for)}`
          : `Realizada: ${formatUtcTimestamp(source.occurred_at ?? source.scheduled_for)}`}
      </time>
    </div>
    <p className={styles.description}>{source.description}</p>
    {cited ? <span className={styles.cited}>Citada por la IA</span> : null}
  </li>;
}
