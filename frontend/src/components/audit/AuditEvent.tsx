import { MutedText } from "@/components/ui/Text";
import { AuditEntry, auditActions, entityLabels, metadataLabels } from "@/lib/audit";
import { formatUtcTimestamp } from "@/lib/date-time";
import styles from "./AuditEvent.module.css";

export function AuditEvent({ entry }: { entry: AuditEntry }) {
  const details = Object.entries(entry.metadata).filter(([key]) => Object.hasOwn(metadataLabels, key));
  return <article className={styles.event}>
    <header className={styles.header}><h2>{auditActions[entry.action] ?? "Evento histórico"}</h2>
      <time dateTime={entry.created_at}>{formatUtcTimestamp(entry.created_at)}</time></header>
    <p>{entry.actor_name ?? (entry.actor_user_id ? "Usuario no disponible" : "Sistema")}</p>
    {entry.actor_user_id ? <MutedText>ID del autor: {entry.actor_user_id}</MutedText> : null}
    <MutedText>{entityLabels[entry.entity_type] ?? "Recurso"} · {entry.entity_id}</MutedText>
    <MutedText>Acción: {entry.action}</MutedText>
    {details.length ? <details className={styles.details}><summary>Ver detalles del evento</summary>
      <dl>{details.map(([key, value]) => <div key={key}><dt>{metadataLabels[key]}</dt>
        <dd>{value === null ? "Sin valor" : typeof value === "string" ? value : JSON.stringify(value)}</dd></div>)}</dl>
    </details> : null}
  </article>;
}
